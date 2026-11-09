from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from lxml import etree

from app.services.pptx_validator import validate_pptx
from app.services.smart_filler_service import SmartFillerService


TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "New_Template_IAV_Resume_CN.pptx"
)


def _shape_with_relationship(slide, relationship_id="rId5"):
    return next(
        shape
        for shape in slide.shapes
        if f'r:id="{relationship_id}"' in shape.element.xml
    )


def test_validator_rejects_raw_shape_copy_with_dangling_relationship(tmp_path):
    presentation = Presentation(TEMPLATE)
    source_slide = presentation.slides[0]
    target_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    shape = _shape_with_relationship(source_slide)
    target_slide.shapes._spTree.insert_element_before(
        deepcopy(shape.element), "p:extLst"
    )
    output = tmp_path / "broken-copy.pptx"
    presentation.save(output)

    result = validate_pptx(str(output))

    assert any(issue.category == "package_integrity" for issue in result.errors)


def test_relationship_aware_shape_copy_produces_valid_package(tmp_path):
    presentation = Presentation(TEMPLATE)
    source_slide = presentation.slides[0]
    target_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    shape = _shape_with_relationship(source_slide)
    cloned = SmartFillerService._clone_shape_element(shape, target_slide)
    target_slide.shapes._spTree.insert_element_before(cloned, "p:extLst")
    SmartFillerService._remove_dangling_shape_tags(presentation)
    output = tmp_path / "valid-copy.pptx"
    presentation.save(output)

    result = validate_pptx(str(output))

    assert not [
        issue for issue in result.errors if issue.category == "package_integrity"
    ]


def test_dangling_office_tags_are_removed_without_losing_text(tmp_path):
    presentation = Presentation(TEMPLATE)
    source_slide = presentation.slides[0]
    target_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    shape = _shape_with_relationship(source_slide)
    target_slide.shapes._spTree.insert_element_before(
        deepcopy(shape.element), "p:extLst"
    )
    expected_text = shape.text

    removed = SmartFillerService._remove_dangling_shape_tags(presentation)
    output = tmp_path / "sanitized-copy.pptx"
    presentation.save(output)
    reopened = Presentation(output)
    result = validate_pptx(str(output))

    assert removed >= 1
    cloned_shape = next(
        candidate
        for candidate in reopened.slides[-1].shapes
        if candidate.text == expected_text
    )
    assert "<p:nvPr" in cloned_shape.element.xml
    assert "<p:tags" not in cloned_shape.element.xml
    assert not [
        issue for issue in result.errors if issue.category == "package_integrity"
    ]


def test_empty_relationship_attribute_is_not_treated_as_dangling(tmp_path):
    presentation = Presentation(TEMPLATE)
    shape = presentation.slides[0].shapes[0]
    relationship_attribute = (
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
    )
    marker = etree.SubElement(shape.element, "{urn:iav:test}optional-reference")
    marker.set(relationship_attribute, "")

    cloned = SmartFillerService._clone_shape_element(
        shape, presentation.slides[0]
    )
    assert next(
        node for node in cloned.iter() if etree.QName(node).localname == "optional-reference"
    ).get(relationship_attribute) == ""
    removed = SmartFillerService._remove_dangling_shape_tags(presentation)
    assert removed >= 0

    output = tmp_path / "empty-relationship-value.pptx"
    presentation.save(output)
    result = validate_pptx(str(output))

    assert not [
        issue for issue in result.errors if issue.category == "package_integrity"
    ]


def test_all_office_tags_are_removed_but_required_nvpr_is_preserved(tmp_path):
    presentation = Presentation(TEMPLATE)
    before = sum(
        1
        for slide in presentation.slides
        for node in slide.element.iter()
        if etree.QName(node).localname == "tags"
    )
    assert before > 0

    removed = SmartFillerService._remove_dangling_shape_tags(presentation)
    output = tmp_path / "tags-removed.pptx"
    presentation.save(output)
    reopened = Presentation(output)

    assert removed == before
    assert not [
        node
        for slide in reopened.slides
        for node in slide.element.iter()
        if etree.QName(node).localname == "tags"
    ]
    for slide in reopened.slides:
        for shape in slide.shapes:
            non_visual = shape.element.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}nvPr")
            if shape.shape_type is not None:
                assert non_visual is not None


def test_company_table_relocation_uses_relationship_aware_clone(tmp_path):
    presentation = Presentation(TEMPLATE)
    company_table, saved_shape, top, _ = SmartFillerService._find_and_save_company_table(
        presentation
    )
    assert company_table is not None
    assert saved_shape is company_table

    SmartFillerService._remove_company_table(presentation)
    target_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    cloned = SmartFillerService._clone_shape_element(saved_shape, target_slide)
    target_slide.shapes._spTree.insert_element_before(cloned, "p:extLst")
    SmartFillerService._remove_dangling_shape_tags(presentation)

    output = tmp_path / "relocated-company-table.pptx"
    presentation.save(output)
    result = validate_pptx(str(output))

    assert not [
        issue for issue in result.errors if issue.category == "package_integrity"
    ]
