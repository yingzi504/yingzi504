<template>
  <div v-if="toolReady" class="salary-workspace">
    <div class="compact-toolbar">
      <el-radio-group v-model="view" :aria-label="t('recruitment.workspaceAria')"><el-radio-button value="salary">{{t('recruitment.salaryTab')}}</el-radio-button><el-radio-button value="social">{{t('recruitment.socialTab')}}</el-radio-button><el-radio-button value="rates">{{t('recruitment.ratesTab')}}</el-radio-button><el-radio-button value="rules">{{t('recruitment.rulesTab')}}</el-radio-button></el-radio-group>
      <div class="actions"><el-button size="small" @click="contextOpen=true">{{t('recruitment.candidateInfo')}}</el-button><el-button size="small" @click="notesOpen=true">{{t('recruitment.instructions')}}</el-button><el-button size="small" @click="loadExample">{{t('recruitment.loadExample')}}</el-button><el-button size="small" type="primary" :icon="Plus" @click="addPlan">{{t('recruitment.addQuote')}}</el-button></div>
    </div>
    <div class="compact-status"><span>{{t('recruitment.statusHint')}}</span><span v-if="exampleLoaded">{{t('recruitment.sourceExample')}} <button @click="clearPlans">{{t('recruitment.clearExample')}}</button></span><span v-if="context.candidate">{{context.candidate}}</span></div>
    <el-dialog v-model="contextOpen" :title="t('recruitment.contextTitle')" width="min(720px, 94vw)">
<div class="context-bar">
      <label><span>{{t('recruitment.candidateCDD')}}</span><el-input v-model="context.candidate" :placeholder="t('recruitment.candidatePlaceholder')" :aria-label="t('recruitment.candidateCDD')" /></label>
      <label><span>{{t('recruitment.ownerPE')}}</span><el-input v-model="context.pe" :placeholder="t('recruitment.ownerPlaceholder')" :aria-label="t('recruitment.ownerPE')" /></label>
      <label><span>{{t('recruitment.positionTitle')}}</span><el-input v-model="context.title" :placeholder="t('recruitment.positionPlaceholder')" :aria-label="t('recruitment.positionTitle')" /></label>
      <label><span>{{t('recruitment.onboardDate')}}</span><el-input v-model="context.onboard" type="date" :aria-label="t('recruitment.onboardDate')" /></label>
    </div>
    </el-dialog>
    <el-dialog v-model="notesOpen" :title="t('recruitment.notesTitle')" width="min(800px, 94vw)">
      <p>{{t('recruitment.notesIntro')}}</p>
            <dl class="formula-notes"><dt>{{t('recruitment.annualPackageTitle')}}</dt><dd>{{t('recruitment.annualPackageFormula')}}</dd><dt>{{t('recruitment.increaseTitle')}}</dt><dd>{{t('recruitment.increaseFormulaLong')}}</dd><dt>{{t('recruitment.rateFormulaTitle')}}</dt><dd>{{t('recruitment.rateFormulaLong')}}</dd><dt>{{t('recruitment.benefitsTitle')}}</dt><dd>{{t('recruitment.benefitsLong')}}</dd><dt>{{t('recruitment.linkageTitle')}}</dt><dd>{{t('recruitment.linkageLong')}}</dd><dt>{{t('recruitment.correctionsTitle')}}</dt><dd>{{t('recruitment.correctionsLong')}}</dd></dl>
    </el-dialog>

    <section v-if="view==='salary'" class="panel">
      <div class="section-heading"><div><h3>{{t('recruitment.salaryTitle')}}</h3><p>{{t('recruitment.salaryDesc')}}</p></div><span class="small-tag">{{t('recruitment.quoteCount',{count:plans.length-1})}}</span></div>
      <div class="table-scroll salary-scroll">
        <table class="salary-table">
          <thead><tr><th>{{t('recruitment.compensationItem')}}</th><th v-for="plan in plans" :key="plan.id" :class="{'current-col':plan.isCurrent}">
            <div class="plan-title"><span v-if="plan.isCurrent">{{t('recruitment.currentSalary')}} <small>{{t('recruitment.baseline')}}</small></span><el-input v-else v-model="plan.name" :aria-label="t('recruitment.nameAria',{name:plan.name})" maxlength="30" />
              <el-dropdown v-if="!plan.isCurrent" trigger="click" @command="(cmd:string)=>planAction(cmd,plan)"><el-button text circle :icon="MoreFilled" :aria-label="t('recruitment.actionAria',{name:plan.name})"/><template #dropdown><el-dropdown-menu><el-dropdown-item command="copy">{{t('recruitment.copyQuote')}}</el-dropdown-item><el-dropdown-item command="remove" :disabled="plans.length<=2">{{t('recruitment.removeQuote')}}</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
            </div>
          </th></tr></thead>
          <tbody>
            <tr><th>{{t('recruitment.payLocation')}}<small>{{t('recruitment.linkedByQuote')}}</small></th><td v-for="plan in plans" :key="plan.id"><span v-if="plan.isCurrent" class="muted">{{t('recruitment.currentCompareOnly')}}</span><el-select v-else v-model="plan.city" :aria-label="t('recruitment.locationAria',{name:plan.name})"><el-option v-for="city in CITY_POLICIES" :key="city.id" :label="cityName(city.id)" :value="city.id"/></el-select></td></tr>
            <tr v-for="field in salaryRows" :key="field.key" :class="{'total-row':field.key==='total'}"><th>{{field.label}}<small>{{field.unit}}</small><el-tooltip v-if="field.hint" :content="field.hint" placement="right"><button class="hint-button" :aria-label="t('recruitment.fieldInfo',{field:field.label})">?</button></el-tooltip></th>
              <td v-for="plan in plans" :key="plan.id" :class="{'locked-cell':isLocked(field.key,plan)}">
                <el-input-number v-if="!isLocked(field.key,plan)" v-model="plan[field.key as InputKey]" :controls="false" :min="0" :max="100000000" :precision="2" :placeholder="t('recruitment.fillPlaceholder')" :aria-label="`${plan.name}${field.label}`"/>
                <template v-else><strong>{{cellValue(field.key,plan)}}</strong><small v-if="field.key==='annualBonus'&&!plan.isCurrent">{{t('recruitment.monthlyTimesTwo')}}</small><small v-if="field.key==='months'">{{t('recruitment.fixedReadonly')}}</small></template>
              </td>
            </tr>
            <tr><th>{{t('recruitment.planNotes')}}</th><td v-for="plan in plans" :key="plan.id"><el-input v-model="plan.note" :placeholder="t('recruitment.planNotesPlaceholder')" :aria-label="t('recruitment.notesAria',{name:plan.name})" maxlength="160"/></td></tr>
          </tbody>
          <tfoot>
            <tr class="total-row"><th>{{t('recruitment.annualPackageTitle')}}<small>{{t('recruitment.packageUnit')}}</small></th><td v-for="plan in plans" :key="plan.id"><strong>{{money(totalPackage(plan))}}</strong></td></tr>
            <tr class="increase-row"><th>{{t('recruitment.packageIncrease')}}<small>{{t('recruitment.increaseFormula')}}</small></th><td v-for="plan in plans" :key="plan.id" class="locked-cell">{{plan.isCurrent?t('recruitment.baselineValue'):percent(increaseRate(plan))}}</td></tr>
            <tr><th>{{t('recruitment.inputStatus')}}</th><td v-for="plan in plans" :key="plan.id"><span :title="localizedMissingFields(plan).join(listSeparator)" :class="missingFields(plan).length?'muted':'complete'">{{missingFields(plan).length?t('recruitment.missingCount',{count:missingFields(plan).length}):t('recruitment.packageCalculated')}}</span></td></tr>
          </tfoot>
        </table>
      </div>
      <div class="panel-foot">{{t('recruitment.packageFoot')}}</div>
    </section>

    <section v-else-if="view==='social'" class="panel">
      <div class="section-heading"><div><h3>{{t('recruitment.socialTitle')}}</h3><p>{{t('recruitment.socialDesc')}}</p></div><el-select v-model="selectedPlanId" :aria-label="t('recruitment.socialQuoteAria')" class="plan-select"><el-option v-for="plan in proposals" :key="plan.id" :label="plan.name" :value="plan.id"/></el-select></div>
      <template v-if="activePlan">
        <div class="social-controls">
          <label><span>{{t('recruitment.location')}}</span><el-select v-model="activePlan.city" :aria-label="t('recruitment.location')"><el-option v-for="city in CITY_POLICIES" :key="city.id" :label="cityName(city.id)" :value="city.id"/></el-select></label>
          <label><span>{{t('recruitment.salarySource')}}</span><el-select v-model="activePlan.contributionMode" :aria-label="t('recruitment.salarySource')"><el-option :label="t('recruitment.newEmployeeSalary')" value="salary"/><el-option :label="t('recruitment.existingEmployeeSalary')" value="priorYear"/></el-select></label>
          <label><span>{{activePlan.contributionMode==='salary'?t('recruitment.quotedSalaryLinked'):t('recruitment.priorYearAverage')}}</span><div v-if="activePlan.contributionMode==='salary'" class="readonly-value">{{money(activePlan.basePay)}}</div><el-input-number v-else v-model="activePlan.priorYearPay" :min="0" :max="100000000" :precision="2" :controls="false" :placeholder="t('recruitment.fillPlaceholder')" :aria-label="t('recruitment.priorYearAverage')"/></label>
        </div>
        <div class="summary-strip"><div><span>{{t('recruitment.employeeMonthly')}}</span><strong>{{money(activeSocial?.employee)}}</strong></div><div><span>{{t('recruitment.employerMonthly')}}</span><strong>{{money(activeSocial?.employer)}}</strong></div><div><span>{{t('recruitment.combinedMonthly')}}</span><strong>{{money(activeSocial?.total)}}</strong></div></div>
        <p class="inline-note">{{t('recruitment.basesNote',{city:cityName(activePlan.city),socialMin:money(activePolicy.socialMin),socialMax:money(activePolicy.socialMax),housingMin:money(activePolicy.housingMin),housingMax:money(activePolicy.housingMax)})}}</p>
        <div v-if="!activeSocial" class="empty-state">{{t('recruitment.fillFirst',{field:activePlan.contributionMode==='salary'?t('recruitment.quotedSalaryLinked'):t('recruitment.priorYearAverage')})}}</div>
        <div v-else class="table-scroll"><table class="detail-table"><thead><tr><th>{{t('recruitment.contributionItem')}}</th><th>{{t('recruitment.contributionBase')}}</th><th>{{t('recruitment.employeeRate')}}</th><th>{{t('recruitment.employeeAmount')}}</th><th>{{t('recruitment.employerRate')}}</th><th>{{t('recruitment.employerAmount')}}</th></tr></thead><tbody><tr v-for="line in activeSocial.lines" :key="line.key"><th>{{contributionName(line.key)}}</th><td>{{line.base===null?'—':money(line.base)}}</td><td>{{rateLabel(line.employeeRate)}}</td><td>{{money(line.employee)}}</td><td>{{rateLabel(line.employerRate)}}</td><td>{{money(line.employer)}}</td></tr></tbody></table></div>
        <div v-if="activePlan.city==='SH'" class="policy-warning">{{t('recruitment.shWarning')}}</div>
        <div class="panel-foot">{{t('recruitment.roundingFoot')}}</div>
      </template>
    </section>

    <section v-else-if="view==='rates'" class="panel">
      <div class="section-heading"><div><h3>{{t('recruitment.ratesTitle')}}</h3><p>{{t('recruitment.ratesDesc')}}</p></div><el-radio-group v-model="rateUnit" size="small" :aria-label="t('recruitment.costUnit')"><el-radio-button value="hourly">Hourly Rate</el-radio-button><el-radio-button value="daily">Daily Rate</el-radio-button></el-radio-group></div>
      <div class="rate-toolbar"><el-checkbox-group v-model="rateCities" :aria-label="t('recruitment.compareLocations')"><el-checkbox v-for="city in CITY_POLICIES" :key="city.id" :value="city.id">{{cityName(city.id)}}</el-checkbox></el-checkbox-group><div class="fixed-caption">{{t('recruitment.fixedCaption')}}</div></div>
      <div class="compact-policy">{{t('recruitment.compactPolicy')}} <button @click="notesOpen=true">{{t('recruitment.viewBasis')}}</button></div>
      <div v-if="!rateCities.length" class="empty-state">{{t('recruitment.selectLocation')}}</div>
      <div v-else class="table-scroll"><table class="rate-table"><thead><tr><th>{{t('recruitment.workLocation')}}</th><th v-for="plan in proposals" :key="plan.id">{{plan.name}}<small>{{t('recruitment.packageShort',{amount:money(totalPackage(plan))})}}</small></th></tr></thead><tbody>
        <tr v-for="city in selectedCities" :key="city.id"><th>{{cityName(city.id)}}<small>{{rateUnit==='hourly'?t('recruitment.perHour'):t('recruitment.perDay')}}</small></th><td v-for="plan in proposals" :key="plan.id"><div class="rate-pair"><span>{{t('recruitment.excludingOverhead')}}<strong>{{money(rateFor(plan,city.id,false))}}</strong></span><span>{{t('recruitment.includingOverhead')}}<strong>{{money(rateFor(plan,city.id,true))}}</strong></span></div><div class="rate-detail">{{t('recruitment.employerMonthlyShort',{amount:money(cityContributions(plan,city.id)?.employer)})}}<span v-if="city.id==='SH'"> · {{t('recruitment.packageDeduction',{amount:money(plan.supplementary)})}}</span></div></td></tr>
      </tbody></table></div>
      <div class="panel-foot">{{t('recruitment.ratesFoot')}}</div>
    </section>

    <section v-else class="panel rules-panel">
      <div class="section-heading"><div><h3>{{t('recruitment.rulesTitle')}}</h3><p>{{t('recruitment.rulesDesc')}}</p></div><el-icon><Lock /></el-icon></div>
      <div class="rule-grid"><div><span>{{t('recruitment.salaryMonths')}}</span><strong>{{t('recruitment.twelveMonths')}}</strong><small>B13:E13</small></div><div><span>{{t('recruitment.quoteBonus')}}</span><strong>{{t('recruitment.monthlyTimesTwo')}}</strong><small>{{t('recruitment.currentEditable')}}</small></div><div><span>{{t('recruitment.annualHours')}}</span><strong>{{t('recruitment.hours1880')}}</strong><small>C21:E30</small></div><div><span>{{t('recruitment.annualOverhead')}}</span><strong>{{t('recruitment.yuan169200')}}</strong><small>C21:E30</small></div></div>
      <div class="table-scroll"><table class="detail-table"><thead><tr><th>{{t('recruitment.workLocation')}}</th><th>{{t('recruitment.socialRange')}}</th><th>{{t('recruitment.housingRange')}}</th><th>{{t('recruitment.housingRates')}}</th><th>{{t('recruitment.source')}}</th></tr></thead><tbody><tr v-for="city in CITY_POLICIES" :key="city.id"><th>{{cityName(city.id)}}</th><td>{{city.socialMin}}–{{city.socialMax}}</td><td>{{city.housingMin}}–{{city.housingMax}}</td><td>{{city.housingBp/100}}% / {{city.housingBp/100}}%</td><td>A{{city.row}}:AN{{city.row}}</td></tr></tbody></table></div>
      <el-button class="rules-explain" text @click="notesOpen=true">{{t('recruitment.fullFormula')}}</el-button>
      <div class="panel-foot">{{t('recruitment.rulesFoot')}}</div>
    </section>
  </div>
  <div v-else class="empty-state">{{t('recruitment.loading')}}</div>
</template>

<script setup lang="ts">
import {computed,onMounted,ref,watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {Plus,MoreFilled,Lock} from '@element-plus/icons-vue'
import http from '@/api/http'
import {CITY_POLICIES,RULES,configureRecruitmentRules,cityPolicy,type Amount,type CityId,type SalaryPlan} from '@/utils/salaryCalculator'
type InputKey='basePay'|'onsite'|'annualBonus'|'projectBonus'|'benefits'|'supplementary'
type RowKey=InputKey|'months'|'total'
const {t,locale}=useI18n()
const salaryRows=computed<{key:RowKey;label:string;unit:string;hint?:string}[]>(()=>[
  {key:'basePay',label:t('recruitment.rows.basePay'),unit:t('recruitment.units.basePay')},
  {key:'months',label:t('recruitment.rows.months'),unit:t('recruitment.units.months')},
  {key:'onsite',label:t('recruitment.rows.onsite'),unit:t('recruitment.units.onsite'),hint:t('recruitment.hints.onsite')},
  {key:'annualBonus',label:t('recruitment.rows.annualBonus'),unit:t('recruitment.units.annualBonus')},
  {key:'projectBonus',label:t('recruitment.rows.projectBonus'),unit:t('recruitment.units.projectBonus')},
  {key:'benefits',label:t('recruitment.rows.benefits'),unit:t('recruitment.units.benefits'),hint:t('recruitment.hints.benefits')},
  {key:'supplementary',label:t('recruitment.rows.supplementary'),unit:t('recruitment.units.supplementary'),hint:t('recruitment.hints.supplementary')},
])
let nextId=1
function makePlan(isCurrent=false):SalaryPlan {const id=nextId++;return {id,name:isCurrent?t('recruitment.defaultCurrent'):t('recruitment.defaultQuote',{number:id-1}),isCurrent,city:'SH',basePay:undefined,onsite:undefined,annualBonus:undefined,projectBonus:undefined,benefits:undefined,supplementary:undefined,contributionMode:'salary',priorYearPay:undefined,note:''}}
const plans=ref<SalaryPlan[]>([makePlan(true),makePlan(),makePlan(),makePlan()])
const toolReady=ref(false)
const calculations=ref<Record<string,any>>({})
const contextOpen=ref(false),notesOpen=ref(false)
const view=ref('salary'),rateUnit=ref('hourly'),selectedPlanId=ref(plans.value[1].id),exampleLoaded=ref(false)
const rateCities=ref<CityId[]>(CITY_POLICIES.map(c=>c.id)),context=ref({candidate:'',pe:'',title:'',onboard:''})
const proposals=computed(()=>plans.value.filter(p=>!p.isCurrent))
const activePlan=computed(()=>proposals.value.find(p=>p.id===selectedPlanId.value)??proposals.value[0])
const activePolicy=computed(()=>cityPolicy(activePlan.value.city))
const activeSocial=computed(()=>cityContributions(activePlan.value,activePlan.value.city))
const selectedCities=computed(()=>CITY_POLICIES.filter(c=>rateCities.value.includes(c.id)))
const money=(value:Amount)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(locale.value,{minimumFractionDigits:2,maximumFractionDigits:2}):'—'
const percent=(value:Amount)=>typeof value==='number'?`${(value*100).toFixed(2)}%`:'—'
const cityName=(id:CityId)=>t(`recruitment.cities.${id}`)
const contributionName=(key:string)=>t(`recruitment.contributions.${key}`)
const rateLabel=(value:string)=>value==='未设置'?t('recruitment.notSet'):value==='固定 3 元'?t('recruitment.fixedThree'):value==='8% · 取整'?t('recruitment.roundedEight'):value
const missingKeyMap:Record<string,InputKey>={'税前月薪':'basePay','驻场津贴':'onsite','年终奖':'annualBonus','项目奖金':'projectBonus','年度福利':'benefits','年包补充公积金':'supplementary'}
const localizedMissingFields=(plan:SalaryPlan)=>missingFields(plan).map(field=>missingKeyMap[field]?t(`recruitment.rows.${missingKeyMap[field]}`):field)
const listSeparator=computed(()=>locale.value==='zh-CN'?'、':', ')
const isLocked=(key:RowKey,p:SalaryPlan)=>key==='months'||key==='total'||(key==='annualBonus'&&!p.isCurrent)
function cellValue(key:RowKey,p:SalaryPlan){return key==='months'?String(RULES.salaryMonths):money(key==='total'?totalPackage(p):annualBonus(p))}
const resultFor=(plan:SalaryPlan)=>calculations.value[String(plan.id)]
const annualBonus=(plan:SalaryPlan):Amount=>resultFor(plan)?.annualBonus
const totalPackage=(plan:SalaryPlan):Amount=>resultFor(plan)?.totalPackage
const missingFields=(plan:SalaryPlan):string[]=>resultFor(plan)?.missingFields||[]
const increaseRate=(plan:SalaryPlan):Amount=>resultFor(plan)?.increaseRate
const cityContributions=(plan:SalaryPlan,city:CityId)=>resultFor(plan)?.cities?.[city]?.contributions
function addPlan(){plans.value.push(makePlan());view.value='salary'}
function planAction(cmd:string,plan:SalaryPlan){if(cmd==='copy')plans.value.push({...plan,id:nextId++,name:t('recruitment.copySuffix',{name:plan.name}).slice(0,30)});if(cmd==='remove'&&proposals.value.length>1){plans.value=plans.value.filter(p=>p.id!==plan.id);if(selectedPlanId.value===plan.id)selectedPlanId.value=proposals.value[0].id}}
function clearPlans(){nextId=1;plans.value=[makePlan(true),makePlan(),makePlan(),makePlan()];selectedPlanId.value=plans.value[1].id;exampleLoaded.value=false}
function loadExample(){clearPlans();const samples=[[18000,0,54000,0,21600,0],[20000,0,40000,0,5800,19200],[25000,0,50000,0,5800,0],[30000,0,60000,0,5800,0]];plans.value.forEach((p,i)=>{[p.basePay,p.onsite,p.annualBonus,p.projectBonus,p.benefits,p.supplementary]=samples[i]});exampleLoaded.value=true;view.value='salary'}
function rateFor(plan:SalaryPlan,city:CityId,overhead:boolean){
  const result=resultFor(plan)?.cities?.[city]?.rates
  if(!result)return undefined
  return rateUnit.value==='daily'?(overhead?result.dailyWithOverhead:result.daily):(overhead?result.hourlyWithOverhead:result.hourly)
}
let calculationTimer:number|undefined
async function calculate(){const result:any=await http.post('/admin/tools/recruitment-calculate',{plans:plans.value.map(({id,isCurrent,city,basePay,onsite,annualBonus,projectBonus,benefits,supplementary,contributionMode,priorYearPay})=>({id,isCurrent,city,basePay,onsite,annualBonus,projectBonus,benefits,supplementary,contributionMode,priorYearPay}))},{skipErrorMessage:true});calculations.value=result.data}
watch(plans,()=>{window.clearTimeout(calculationTimer);calculationTimer=window.setTimeout(()=>void calculate(),150)},{deep:true})
watch(locale,()=>{plans.value.forEach(plan=>{if(plan.isCurrent){plan.name=t('recruitment.defaultCurrent');return}if(/^(报价|Quote)\s+\d+$/.test(plan.name))plan.name=t('recruitment.defaultQuote',{number:plan.id-1})})})
onMounted(async()=>{const result:any=await http.get('/admin/tools/recruitment-config');configureRecruitmentRules(result.data);rateCities.value=CITY_POLICIES.map(c=>c.id);await calculate();toolReady.value=true})
</script>

<style scoped>
.salary-workspace{height:100%;min-height:0;overflow:auto;padding:2px 2px 18px;color:#302a3d;scrollbar-gutter:stable;font-size:12px}.workspace-top,.section-heading,.workspace-nav,.actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.workspace-top h2{font-size:20px;font-weight:600;line-height:1.5}.workspace-top p,.section-heading p{font-size:12px;color:#82798d;margin:5px 0 0;line-height:1.6}.actions{flex-shrink:0}.actions .el-button+.el-button{margin-left:0}.source-notice{color:#81728f;background:var(--app-primary-soft);border:1px solid var(--app-primary-light-8);border-radius:6px;padding:8px 12px;margin:12px 0;font-size:11px;line-height:1.6}.context-bar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;padding:12px 14px;background:white;border:1px solid #e7e3ed;border-radius:9px}.context-bar label,.social-controls label{display:flex;flex-direction:column;gap:6px;min-width:0}.context-bar label>span,.social-controls label>span{font-size:11px;color:#82798d}.workspace-nav{margin:14px 0;flex-wrap:wrap}.legend{display:flex;gap:14px;color:#8c8396;font-size:11px}.legend span{display:flex;align-items:center;gap:5px}.legend i{width:12px;height:12px;border:1px solid #d7d1e0;border-radius:2px}.editable-dot{background:#fff}.locked-dot{background:#eeedf2}.panel{background:white;border:1px solid #e4e0eb;border-radius:10px;overflow:hidden}.section-heading{padding:14px 16px}.section-heading h3{font-size:14px;margin:0;font-weight:600}.small-tag{color:var(--app-primary-dark);white-space:nowrap;background:var(--app-primary-soft);border-radius:5px;padding:5px 8px}.table-scroll{overflow:auto;max-height:calc(100vh - 325px);min-height:180px}.salary-scroll{max-height:calc(100vh - 350px)}table{border-collapse:separate;border-spacing:0;width:100%;table-layout:fixed;font-size:12px}th,td{padding:9px 12px;border-bottom:1px solid #ebe8f0;line-height:1.5;overflow-wrap:anywhere;text-align:right;font-variant-numeric:tabular-nums}th{font-weight:500;color:#60536c}thead th{position:sticky;top:0;z-index:2;background:#f6f3fa;border-bottom:1px solid #ded6e7;text-align:left}thead th:first-child{left:0;z-index:3}tbody th{position:sticky;left:0;z-index:1;background:white;text-align:left}th small,td>small{display:block;color:#93869f;font-size:10px;font-weight:400;margin-top:2px}td strong{font-size:13px;font-weight:500}td .el-input-number,td .el-select{width:100%}.salary-table th,.salary-table td{width:195px}.salary-table th:first-child{width:215px}.salary-table td.locked-cell{background:#f0eff3}.salary-table td{vertical-align:middle}.salary-table :deep(.el-input-number .el-input__inner){text-align:right}.salary-table :deep(.el-input__wrapper){background:white}.salary-table .total-row th,.salary-table .total-row td{background:var(--app-primary-soft);color:var(--app-primary-dark);border-top:1px solid var(--app-primary-light-7)}.total-row strong{font-size:19px;font-weight:600}.increase-row td{color:var(--app-primary-dark)}.plan-title{display:flex;gap:4px;align-items:center;min-height:32px}.plan-title>.el-input{flex:1;min-width:0}.plan-title :deep(.el-input__wrapper){box-shadow:none;background:transparent;padding:0}.plan-title :deep(input){font-weight:600;color:#463152}.plan-title small{font-weight:400;margin-left:5px;color:#998aa6;font-size:10px}.current-col{border-top:3px solid #b2aab9}.salary-table thead th:not(:first-child):not(.current-col){border-top:3px solid var(--app-primary)}.hint-button{border:1px solid #d2c8dc;background:#fff;color:#9e8bab;width:15px;height:15px;border-radius:50%;font-size:10px;padding:0;line-height:13px;cursor:help;margin-top:4px}.muted{font-size:11px;color:#9a91a4}.complete{color:#64785e;font-size:11px}.panel-foot{padding:10px 16px;font-size:11px;color:#92859f;line-height:1.7}.plan-select{width:180px}.social-controls{display:grid;grid-template-columns:1fr 1.5fr 1fr;gap:16px;padding:0 16px 16px}.social-controls .el-input-number{width:100%}.readonly-value{height:32px;padding:7px 12px;background:#f0eff3;border:1px solid #e0dce7;border-radius:4px;box-sizing:border-box;color:#63586f}.summary-strip{display:grid;grid-template-columns:repeat(3,1fr);margin:0 16px;border-top:1px solid #e8e0ef;border-bottom:1px solid #e8e0ef;background:var(--app-primary-surface)}.summary-strip>div{padding:14px 16px}.summary-strip span{display:block;color:#8f7d9c;font-size:11px;margin-bottom:7px}.summary-strip strong{font-size:22px;font-weight:600;color:var(--app-primary-dark);font-variant-numeric:tabular-nums}.inline-note{margin:12px 16px;line-height:1.7;font-size:11px;color:#8e7f9a}.detail-table{min-width:790px}.detail-table tbody td{background:#f5f4f7}.detail-table thead th{width:145px}.detail-table thead th:first-child{width:155px}.detail-table tbody th{background:#faf9fc}.policy-warning,.example-notice{margin:10px 16px;padding:8px 11px;border-left:3px solid #c6a75f;background:#fcf9f1;color:#8c7549;font-size:11px;line-height:1.8}.example-notice{margin:0 0 12px}.example-notice button{border:none;background:transparent;color:var(--app-primary-dark);cursor:pointer;text-decoration:underline;font-size:11px;margin-left:10px}.empty-state{padding:36px 20px;text-align:center;color:#9a8ba4}.rate-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px;justify-content:space-between;padding:0 16px 8px}.fixed-caption{font-size:11px;color:#95869e}.rate-table th,.rate-table td{width:220px}.rate-table th:first-child{width:230px}.rate-table thead th{color:#594168}.rate-table td{font-size:16px;font-weight:500}.city-band th{background:#eeebf3;padding:7px 14px;font-size:12px}.city-band span{color:#9e8fab;font-size:10px;margin-left:8px}.rate-highlight th,.rate-highlight td{background:var(--app-primary-surface);color:var(--app-primary-dark)}.rule-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 16px 16px}.rule-grid>div{padding:14px;background:#f0eff3;border:1px solid #e5e0ea;border-radius:6px}.rule-grid span,.rule-grid small{display:block;font-size:11px;color:#8f8399}.rule-grid strong{display:block;font-size:20px;font-weight:600;margin:9px 0;color:#62536f}.formula-notes{display:grid;grid-template-columns:155px 1fr;gap:14px 18px;margin:20px 16px;font-size:12px;line-height:1.8}.formula-notes dt{color:#5e456e;font-weight:500}.formula-notes dd{margin:0;color:#8a7b95}button:focus-visible{outline:2px solid var(--app-primary);outline-offset:3px}
@media(max-width:1100px){.workspace-nav{align-items:flex-start}.legend{width:100%}.workspace-top h2{font-size:18px}.rule-grid{grid-template-columns:repeat(2,1fr)}.context-bar{grid-template-columns:repeat(2,minmax(0,1fr))}.salary-scroll{max-height:550px}.table-scroll{max-height:600px}}
@media(max-width:760px){.salary-workspace{height:auto;overflow:visible}.workspace-top,.section-heading{align-items:flex-start;flex-direction:column}.actions{width:100%}.workspace-nav :deep(.el-radio-group){display:flex;flex-wrap:wrap;gap:7px}.workspace-nav :deep(.el-radio-button__inner){border:1px solid #dcdfe6;border-radius:5px!important;box-shadow:none!important;font-size:11px;padding:8px 10px}.social-controls{grid-template-columns:1fr}.summary-strip>div{padding:10px 7px}.summary-strip strong{font-size:16px}.formula-notes{grid-template-columns:1fr;gap:5px}.formula-notes dd{margin-bottom:12px}.salary-table th:first-child{width:150px}.rate-table th:first-child{width:165px}.context-bar{gap:10px;padding:10px}.legend{font-size:10px}.table-scroll{max-height:550px}.rule-grid strong{font-size:17px}}

.context-details{margin:0;background:#fff;border:1px solid #e7e3ed;border-radius:6px}.context-details summary{padding:8px 12px;color:#8c7c97;cursor:pointer;font-size:11px}.context-details .context-bar{border:none;border-top:1px solid #eee9f3;border-radius:0}.salary-table tfoot{position:sticky;bottom:0;z-index:3}.salary-table tfoot td,.salary-table tfoot th{background:#f3f0f8;padding-top:6px;padding-bottom:6px}.salary-table tfoot th{position:sticky;left:0;z-index:4;text-align:left}.salary-table tfoot .total-row td,.salary-table tfoot .total-row th{background:#efe5ff}.salary-table tfoot tr:last-child td,.salary-table tfoot tr:last-child th{font-size:10px;padding-top:3px;padding-bottom:3px}
@media(min-width:761px){.salary-workspace{display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;padding-bottom:0}.salary-workspace>*{flex-shrink:0}.salary-workspace>.panel{flex:1;min-height:180px;display:flex;flex-direction:column}.panel>*{flex-shrink:0}.panel>.table-scroll{flex:1;min-height:80px;max-height:none}.salary-workspace>.rules-panel{overflow:auto;display:block}.rules-panel>.table-scroll{max-height:none}.salary-table th,.salary-table td{padding-top:6px;padding-bottom:6px}.hint-button{float:right;margin-top:-15px}.workspace-top p{margin-top:2px}.workspace-top h2{font-size:18px}.workspace-nav{margin:10px 0}.source-notice{margin:8px 0}.section-heading{padding-top:10px;padding-bottom:10px}}

.compact-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}.compact-toolbar :deep(.el-radio-button__inner){padding:8px 12px;font-size:12px}.compact-status{display:flex;justify-content:space-between;gap:12px;font-size:11px;color:#897b95;padding:6px 0 8px;line-height:1.5}.compact-status button,.compact-policy button{border:0;background:none;color:var(--app-primary-dark);cursor:pointer;font-size:11px}.compact-policy{font-size:11px;color:#8c7549;padding:4px 16px 8px}.rate-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.rate-pair>span{font-size:10px;color:#8a7c95}.rate-pair strong{display:block;font-size:16px;color:#5e486b;margin-top:2px}.rate-pair>span:last-child strong{color:var(--app-primary-dark)}.rate-detail{font-size:10px;color:#96889f;margin-top:5px;font-weight:400}.rules-explain{align-self:flex-start;margin:8px 16px}.rate-table th:first-child{width:120px}.rate-table td{padding:4px 12px}.formula-notes{margin:16px 0}.salary-table th small{display:inline;font-size:10px;margin-left:6px}.salary-table td>small{display:inline;margin-left:8px}.salary-table th:first-child{width:220px}.salary-table tbody th small{display:none}.salary-table tbody th{font-size:12px}.salary-table tbody th:has(small){line-height:1.5}.salary-table .hint-button{float:none;margin:0 0 0 6px}.salary-table tfoot{position:static}.salary-table tfoot th{position:sticky}.salary-table .total-row strong{font-size:17px}
@media(min-width:761px){.panel .section-heading{padding:8px 12px}.section-heading p{font-size:11px;margin-top:2px}.salary-table th,.salary-table td{padding:4px 10px}.salary-table :deep(.el-input__wrapper){min-height:28px}.salary-table :deep(.el-input__inner){height:28px;font-size:12px}.salary-table :deep(.el-select__wrapper){min-height:28px;font-size:12px}.plan-title{min-height:28px}.panel-foot{padding:6px 12px;font-size:10px}.social-controls{padding:0 12px 8px;gap:12px}.summary-strip{margin:0 12px}.summary-strip>div{display:flex;align-items:center;gap:12px;padding:9px 12px}.summary-strip span{margin:0}.summary-strip strong{font-size:19px}.inline-note{margin:6px 12px}.policy-warning{padding:5px 10px;margin:6px 12px}.detail-table th,.detail-table td{padding:8px 10px}.rate-toolbar{padding:0 12px 4px}.rule-grid{margin:0 12px 10px}.rule-grid>div{padding:10px}.rule-grid strong{font-size:18px;margin:5px 0}.salary-table tfoot td,.salary-table tfoot th{padding:4px 10px}.salary-workspace>.panel{min-height:0}}
@media(max-width:760px){.compact-toolbar .actions{flex-wrap:wrap;justify-content:flex-start;gap:6px}.compact-toolbar :deep(.el-radio-group){gap:4px}.compact-toolbar :deep(.el-radio-button__inner){padding:7px 8px;font-size:11px}.compact-status{flex-wrap:wrap}.rate-table th:first-child{width:100px}.salary-table th:first-child{width:160px}}
</style>
