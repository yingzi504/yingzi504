/** Source: 薪资计算.xlsx / 招聘工具. No policy values are inferred from current law. */
export type CityId = 'SH' | 'BJ' | 'HF' | 'SY' | 'WH'
export type Amount = number | undefined | null
export interface CityPolicy {
  readonly id: CityId
  readonly name: string
  readonly row: number
  readonly socialMin: number
  readonly socialMax: number
  readonly housingMin: number
  readonly housingMax: number
  readonly medicalBp: number
  readonly injuryBp: number
  readonly housingBp: number
  readonly supplementalBp: number
  readonly seriousMedical: number
}
export const RULES = { salaryMonths: 0, bonusMonths: 0, annualHours: 0, overhead: 0, dailyHours: 0 }
export const CITY_POLICIES: CityPolicy[] = []
export function configureRecruitmentRules(config:{rules:typeof RULES;cities:CityPolicy[]}) {
  Object.assign(RULES, config.rules)
  CITY_POLICIES.splice(0, CITY_POLICIES.length, ...config.cities.map(city => Object.freeze({...city})))
}
export const cityPolicy = (id:CityId) => CITY_POLICIES.find(p => p.id === id)!
export const isAmount = (v:Amount): v is number => typeof v === 'number' && Number.isFinite(v) && v >= 0
const cents = (n:number) => Math.round(n * 100)
const sum = (items:number[]) => items.reduce((a,b) => a + cents(b),0) / 100

export interface SalaryPlan {
  id:number; name:string; city:CityId; isCurrent:boolean
  basePay:Amount; onsite:Amount; annualBonus:Amount; projectBonus:Amount; benefits:Amount; supplementary:Amount
  contributionMode:'salary'|'priorYear'; priorYearPay:Amount; note:string
}
export function annualBonus(plan:SalaryPlan):Amount {
  return plan.isCurrent ? plan.annualBonus : isAmount(plan.basePay) ? cents(plan.basePay)*RULES.bonusMonths/100 : undefined
}
export function totalPackage(plan:SalaryPlan):number|undefined {
  const parts=[plan.basePay,plan.onsite,annualBonus(plan),plan.projectBonus,plan.benefits,plan.supplementary]
  if(!parts.every(isAmount)) return undefined
  return sum([parts[0]*RULES.salaryMonths,...parts.slice(1)])
}
export function missingFields(plan:SalaryPlan):string[] {
  return ([['税前月薪',plan.basePay],['驻场津贴',plan.onsite],['年终奖',annualBonus(plan)],['项目奖金',plan.projectBonus],['年度福利',plan.benefits],['年包补充公积金',plan.supplementary]] as [string,Amount][]).filter(([,v])=>!isAmount(v)).map(([name])=>name)
}
export function increaseRate(total:Amount,baseline:Amount):number|undefined {
  if(!isAmount(total)||!isAmount(baseline)||baseline===0) return undefined
  const delta=cents(total)-cents(baseline)
  // Excel ROUND(...,2): half away from zero, then display as a percentage.
  return Math.sign(delta)*Math.floor(Math.abs(delta)*100/cents(baseline)+0.5)/100
}
export const contributionSalary=(plan:SalaryPlan):Amount => plan.contributionMode==='priorYear'?plan.priorYearPay:plan.basePay
export interface ContributionLine { key:string; name:string; base:number|null; employeeRate:string; employerRate:string; employee:number; employer:number }
export interface Contributions { socialBase:number; housingBase:number; lines:ContributionLine[]; employee:number; employer:number; total:number }
export function contributions(city:CityId,salary:Amount):Contributions|undefined {
  if(!isAmount(salary)) return undefined
  const p=cityPolicy(city)
  const clamp=(min:number,max:number)=>Math.max(min,Math.min(max,cents(salary)/100))
  const socialBase=city==='SH'?Math.round(clamp(p.socialMin,p.socialMax)):clamp(p.socialMin,p.socialMax)
  const housingBase=city==='SH'?Math.round(clamp(p.housingMin,p.housingMax)):clamp(p.housingMin,p.housingMax)
  // Integer cents × basis points avoids floating-point ROUNDUP overcharging an exact tenth.
  const fee=(base:number,bp:number,mode:'up1'|'round2'|'round0')=>{
    const product=cents(base)*bp
    if(mode==='up1') return Math.ceil(product/100000)/10
    if(mode==='round0') return Math.floor(product/1000000+0.5)
    return Math.floor(product/10000+0.5)/100
  }
  const pct=(bp:number)=>`${bp/100}%`
  const lines:ContributionLine[]=[
    {key:'pension',name:'养老保险',base:socialBase,employeeRate:'8%',employerRate:'16%',employee:fee(socialBase,800,'up1'),employer:fee(socialBase,1600,'round2')},
    {key:'medical',name:'医疗保险',base:socialBase,employeeRate:'2%',employerRate:pct(p.medicalBp),employee:fee(socialBase,200,'up1'),employer:fee(socialBase,p.medicalBp,'round2')},
    {key:'serious',name:'大病医疗',base:null,employeeRate:p.seriousMedical?'固定 3 元':'未设置',employerRate:'未设置',employee:p.seriousMedical,employer:0},
    {key:'unemployment',name:'失业保险',base:socialBase,employeeRate:'0.5%',employerRate:'0.5%',employee:fee(socialBase,50,'up1'),employer:fee(socialBase,50,'round2')},
    {key:'maternity',name:'生育保险',base:socialBase,employeeRate:'未设置',employerRate:'0.8%',employee:0,employer:fee(socialBase,80,'round2')},
    {key:'injury',name:'工伤保险',base:socialBase,employeeRate:'未设置',employerRate:pct(p.injuryBp),employee:0,employer:fee(socialBase,p.injuryBp,'round2')},
    {key:'housing',name:'住房公积金',base:housingBase,employeeRate:pct(p.housingBp),employerRate:pct(p.housingBp),employee:fee(housingBase,p.housingBp,'round0'),employer:fee(housingBase,p.housingBp,'round0')},
    {key:'supplemental',name:'补充公积金',base:housingBase,employeeRate:'未设置',employerRate:p.supplementalBp?'8% · 取整':'未设置',employee:0,employer:fee(housingBase,p.supplementalBp,'round0')},
  ]
  const employee=sum(lines.map(l=>l.employee)),employer=sum(lines.map(l=>l.employer))
  return {socialBase,housingBase,lines,employee,employer,total:sum([employee,employer])}
}
export function hourlyRates(total:Amount,employerMonthly:Amount) {
  if(!isAmount(total)||!isAmount(employerMonthly)) return undefined
  const annualCost=sum([total,employerMonthly*12]),withOverhead=sum([annualCost,RULES.overhead])
  return {annualCost,withOverhead,hourly:annualCost/RULES.annualHours,hourlyWithOverhead:withOverhead/RULES.annualHours,daily:annualCost/RULES.annualHours*RULES.dailyHours,dailyWithOverhead:withOverhead/RULES.annualHours*RULES.dailyHours}
}

/** Each quotation owns its payroll input. Beijing uses its own cost (user-confirmed correction of C26:E26). */
export function quotationRates(plan:SalaryPlan,city:CityId=plan.city) {
  const total=totalPackage(plan)
  if(total===undefined || !isAmount(plan.supplementary)) return undefined
  // Actual Shanghai supplemental payments are included in contributions below.
  // Remove the package disclosure first, including when caps or prior-year pay differ.
  const packageSupplementDeduction=city==='SH'?plan.supplementary:0
  const costPackage=sum([total,-packageSupplementDeduction])
  const result=hourlyRates(costPackage,contributions(city,contributionSalary(plan))?.employer)
  return result?{...result,packageSupplementDeduction,costPackage}:undefined
}
