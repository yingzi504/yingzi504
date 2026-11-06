import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from '../node_modules/typescript/lib/typescript.js'

const code=ts.transpileModule(readFileSync(new URL('../src/utils/salaryCalculator.ts',import.meta.url),'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.ES2020}}).outputText
const {CITY_POLICIES,contributions,totalPackage,annualBonus,increaseRate,quotationRates}=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)
const plan=(overrides={})=>({id:2,name:'报价 1',city:'SH',isCurrent:false,basePay:20000,onsite:0,annualBonus:40000,projectBonus:0,benefits:5800,supplementary:19200,contributionMode:'salary',priorYearPay:undefined,note:'',...overrides})
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`)

test('five city totals include corrected single Shanghai supplemental contribution',()=>{
  const expected={SH:[3500,8592,12092],BJ:[4503,7700,12203],HF:[4500,7180,11680],SY:[4500,7720,12220],WH:[4500,7700,12200]}
  for(const [city,values] of Object.entries(expected)){
    const result=contributions(city,20000)
    assert.deepEqual([result.employee,result.employer,result.total],values)
    near(result.lines.reduce((s,l)=>s+l.employee,0),values[0])
    near(result.lines.reduce((s,l)=>s+l.employer,0),values[1])
  }
})
test('annual packages and Excel-rounded increases match B19:E20',()=>{
  const baseline=totalPackage(plan({isCurrent:true,basePay:18000,annualBonus:54000,benefits:21600,supplementary:0}))
  assert.equal(baseline,291600)
  const inputs=[plan(),plan({basePay:25000,supplementary:0}),plan({basePay:30000,supplementary:0})]
  assert.deepEqual(inputs.map(totalPackage),[305000,355800,425800])
  assert.deepEqual(inputs.map(p=>increaseRate(totalPackage(p),baseline)),[0.05,0.22,0.46])
  assert.equal(increaseRate(995,1000),-0.01)
  assert.equal(increaseRate(1005,1000),0.01)
})
test('rates include Shanghai deduplication and Beijing reference correction',()=>{
  const expected={SH:[206.863829787234,296.863829787234],BJ:[211.382978723404,301.382978723404],HF:[208.063829787234,298.063829787234],SY:[211.510638297872,301.510638297872],WH:[211.382978723404,301.382978723404]}
  for(const [city,[without,withOverhead]] of Object.entries(expected)){
    const result=quotationRates(plan(),city)
    near(result.hourly,without);near(result.hourlyWithOverhead,withOverhead)
    near(result.daily,result.hourly*8)
    near(result.dailyWithOverhead-result.daily,720)
  }
  assert.notEqual(quotationRates(plan(),'BJ').hourly,quotationRates(plan(),'HF').hourly)
})
test('new quotation salary and prior-year payroll independently drive contributions',()=>{
  const higher=plan({basePay:25000,supplementary:0})
  assert.notEqual(quotationRates(higher).annualCost,totalPackage(higher)+8592*12)
  higher.contributionMode='priorYear'
  assert.equal(quotationRates(higher),undefined)
  higher.priorYearPay=20000
  assert.equal(quotationRates(higher).annualCost,totalPackage(higher)+8592*12)
})
test('all social and housing caps/floors and Shanghai integer rounding',()=>{
  for(const p of CITY_POLICIES){
    for(const [salary,expectedSocial,expectedHousing] of [[0,p.socialMin,p.housingMin],[100000,p.socialMax,p.housingMax],[p.socialMin,p.socialMin,Math.max(p.housingMin,Math.min(p.housingMax,p.socialMin))]]){
      const r=contributions(p.id,salary)
      assert.equal(r.socialBase,expectedSocial);assert.equal(r.housingBase,expectedHousing)
    }
  }
  assert.equal(contributions('SH',8000.50).socialBase,8001)
  assert.equal(contributions('BJ',8000.50).socialBase,8000.50)
})
test('round-up does not add an extra tenth due to floating-point multiplication',()=>{
  const exact=contributions('BJ',8001.25),fraction=contributions('BJ',8001.26)
  assert.equal(exact.lines[0].employee,640.1)
  assert.equal(fraction.lines[0].employee,640.2)
  assert.equal(fraction.lines[0].employer,1280.20)
  assert.equal(contributions('BJ',10004.17).lines.find(l=>l.key==='housing').employee,1201)
})
test('blank versus zero and invalid inputs remain distinguishable',()=>{
  for(const value of [undefined,null,NaN,-1,Infinity]){
    assert.equal(contributions('SH',value),undefined)
    assert.equal(totalPackage(plan({onsite:value})),undefined)
  }
  assert.equal(totalPackage(plan({onsite:0})),305000)
  assert.equal(increaseRate(100,0),undefined)
  assert.equal(annualBonus(plan({basePay:0})),0)
  assert.equal(annualBonus(plan({isCurrent:true,annualBonus:123})),123)
  assert.equal(totalPackage(plan({basePay:100000000})),1400025000)
})

// Independent cost composition: cash/benefits exclude the package disclosure;
// basic contributions 6,992/month + one supplemental payment 1,600/month.
test('Shanghai counts supplemental once, keeps candidate package, and preserves basic housing',()=>{
  const p=plan(), c=contributions('SH',20000), r=quotationRates(p)
  assert.equal(c.lines.find(l=>l.key==='housing').employer,1400)
  assert.equal(c.lines.find(l=>l.key==='supplemental').employer,1600)
  assert.equal(totalPackage(p),305000)
  assert.equal(r.packageSupplementDeduction,19200)
  assert.equal(r.annualCost,285800+6992*12+1600*12)
  assert.equal(r.annualCost,388904)
  assert.equal(r.withOverhead,558104)
  near(r.daily,1654.910638297872)
  near(r.dailyWithOverhead,2374.910638297872)
})
test('Shanghai deduplication is robust to manual amounts, zero, caps and prior-year payroll',()=>{
  for(const supplementary of [0,12345,19200,50000]){
    assert.equal(quotationRates(plan({supplementary})).annualCost,388904)
  }
  const capped=plan({basePay:50000,supplementary:48000})
  const c=contributions('SH',50000)
  assert.equal(c.lines.find(l=>l.key==='supplemental').employer,3018)
  assert.equal(quotationRates(capped).annualCost,705800+c.employer*12)
  const prior=plan({contributionMode:'priorYear',priorYearPay:10000})
  assert.equal(quotationRates(prior).annualCost,285800+contributions('SH',10000).employer*12)
  assert.equal(quotationRates(plan({supplementary:null})),undefined)
  assert.equal(quotationRates(plan(),'BJ').packageSupplementDeduction,0)
})
