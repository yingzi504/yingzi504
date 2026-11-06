<template>
  <div class="salary-workspace">
    <div class="compact-toolbar">
      <el-radio-group v-model="view" aria-label="招聘工具工作区"><el-radio-button value="salary">薪资方案</el-radio-button><el-radio-button value="social">社保确认</el-radio-button><el-radio-button value="rates">Hourly / Daily Rate</el-radio-button><el-radio-button value="rules">固定规则</el-radio-button></el-radio-group>
      <div class="actions"><el-button size="small" @click="contextOpen=true">候选人信息</el-button><el-button size="small" @click="notesOpen=true">使用说明</el-button><el-button size="small" @click="loadExample">载入原表示例</el-button><el-button size="small" type="primary" :icon="Plus" @click="addPlan">新增报价</el-button></div>
    </div>
    <div class="compact-status"><span>白色可填 · 灰色固定 / 自动计算 · 输入仅本页有效，刷新后清空</span><span v-if="exampleLoaded">原表示例 <button @click="clearPlans">清空示例</button></span><span v-if="context.candidate">{{context.candidate}}</span></div>
    <el-dialog v-model="contextOpen" title="候选人信息（选填）" width="min(720px, 94vw)">
<div class="context-bar">
      <label><span>候选人 CDD</span><el-input v-model="context.candidate" placeholder="姓名或代号" aria-label="候选人 CDD" /></label>
      <label><span>负责人 PE</span><el-input v-model="context.pe" placeholder="负责人" aria-label="负责人 PE" /></label>
      <label><span>职位 Title</span><el-input v-model="context.title" placeholder="拟入职职位" aria-label="职位 Title" /></label>
      <label><span>预计入职日期</span><el-input v-model="context.onboard" type="date" aria-label="预计入职日期" /></label>
    </div>
    </el-dialog>
    <el-dialog v-model="notesOpen" title="使用说明与计算口径" width="min(800px, 94vw)">
      <p>依据《薪资计算.xlsx》测算，政策生效日期未提供。输入仅保留本页，刷新或离开后清空。原表示例的各报价已分别联动基数，可能与原表共用 20,000 元基数时不同。</p>
            <dl class="formula-notes"><dt>候选人年包</dt><dd>月薪 × 12 + 驻场津贴 + 年终奖 + 项目奖金 + 年度福利 + 年包补充公积金。除月薪外均为年度金额。</dd><dt>涨幅</dt><dd>ROUND((报价年包 − 当前年包) ÷ 当前年包, 2)，保留原表先取两位小数再显示百分比的规则。</dd><dt>Hourly / Daily Rate</dt><dd>(年包 − 上海年包已含补充公积金 + 公司月缴费 × 12 + 可选 Overhead) ÷ 1,880；Daily Rate = 未取整的 Hourly Rate × 8，展示时保留两位小数。</dd><dt>福利与补充公积金</dt><dd>白色字段允许手填。原表福利示例为 1,800 + 1,100 + 1,100 + 1,200 + 600 = 5,800；未提供各项名称或性别、销售电话费规则，因此不自动分配。上海年包补充公积金示例为月薪 × 8% × 12，需核对城市后填写。</dd><dt>与原表的联动差异</dt><dd>每份报价使用自己的月薪计算缴费，不再共用 B3:B7 的工资输入。老员工可输入上年度月平均工资。</dd><dt>原表差异与保留口径</dt><dd>北京 C26:E26 原引用合肥 AM5，已按用户确认改为北京对应成本（AM4）。上海原 AL3 乘 2 且年包另计一份，已按用户确认取消倍乘，并在企业成本中扣除年包已含补充公积金，改按实际缴费计一次。</dd></dl>
    </el-dialog>

    <section v-if="view==='salary'" class="panel">
      <div class="section-heading"><div><h3>当前薪资与报价</h3><p>月薪以元 / 月录入，其余金额以元 / 年录入。无此项请填 0，空白不计为 0。</p></div><span class="small-tag">{{ plans.length-1 }} 份报价 · CNY</span></div>
      <div class="table-scroll salary-scroll">
        <table class="salary-table">
          <thead><tr><th>薪酬项目</th><th v-for="plan in plans" :key="plan.id" :class="{'current-col':plan.isCurrent}">
            <div class="plan-title"><span v-if="plan.isCurrent">当前薪资 <small>涨幅基准</small></span><el-input v-else v-model="plan.name" :aria-label="`${plan.name}名称`" maxlength="30" />
              <el-dropdown v-if="!plan.isCurrent" trigger="click" @command="(cmd:string)=>planAction(cmd,plan)"><el-button text circle :icon="MoreFilled" :aria-label="`${plan.name}操作`"/><template #dropdown><el-dropdown-menu><el-dropdown-item command="copy">复制报价</el-dropdown-item><el-dropdown-item command="remove" :disabled="plans.length<=2">移除报价</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
            </div>
          </th></tr></thead>
          <tbody>
            <tr><th>社保公积金缴纳地<small>按报价分别联动</small></th><td v-for="plan in plans" :key="plan.id"><span v-if="plan.isCurrent" class="muted">当前薪资仅用于年包比较</span><el-select v-else v-model="plan.city" :aria-label="`${plan.name}缴纳地`"><el-option v-for="city in CITY_POLICIES" :key="city.id" :label="city.name" :value="city.id"/></el-select></td></tr>
            <tr v-for="field in salaryRows" :key="field.key" :class="{'total-row':field.key==='total'}"><th>{{field.label}}<small>{{field.unit}}</small><el-tooltip v-if="field.hint" :content="field.hint" placement="right"><button class="hint-button" :aria-label="`${field.label}说明`">?</button></el-tooltip></th>
              <td v-for="plan in plans" :key="plan.id" :class="{'locked-cell':isLocked(field.key,plan)}">
                <el-input-number v-if="!isLocked(field.key,plan)" v-model="plan[field.key as InputKey]" :controls="false" :min="0" :max="100000000" :precision="2" placeholder="待填写" :aria-label="`${plan.name}${field.label}`"/>
                <template v-else><strong>{{cellValue(field.key,plan)}}</strong><small v-if="field.key==='annualBonus'&&!plan.isCurrent">月薪 × 2</small><small v-if="field.key==='months'">固定，不可修改</small></template>
              </td>
            </tr>
            <tr><th>方案备注</th><td v-for="plan in plans" :key="plan.id"><el-input v-model="plan.note" placeholder="谈薪备注（选填）" :aria-label="`${plan.name}备注`" maxlength="160"/></td></tr>
          </tbody>
          <tfoot>
            <tr class="total-row"><th>候选人年包<small>Total Package · 元 / 年</small></th><td v-for="plan in plans" :key="plan.id"><strong>{{money(totalPackage(plan))}}</strong></td></tr>
            <tr class="increase-row"><th>年包涨幅<small>按原表 ROUND(涨幅, 2)</small></th><td v-for="plan in plans" :key="plan.id" class="locked-cell">{{plan.isCurrent?'基准':percent(increaseRate(totalPackage(plan),currentTotal))}}</td></tr>
            <tr><th>录入状态</th><td v-for="plan in plans" :key="plan.id"><span :title="missingFields(plan).join('、')" :class="missingFields(plan).length?'muted':'complete'">{{missingFields(plan).length?`待填 ${missingFields(plan).length} 项`:'年包已计算'}}</span></td></tr>
          </tfoot>
        </table>
      </div>
      <div class="panel-foot">Total Package 为原表给候选人展示的年包，包含所填福利及补充公积金，不等同于税后到手收入。当前年包为空或为 0 时，不计算涨幅。</div>
    </section>

    <section v-else-if="view==='social'" class="panel">
      <div class="section-heading"><div><h3>五险一金金额确认</h3><p>选择一份报价，查看该缴纳地每个险种的基数、比例和月度金额。</p></div><el-select v-model="selectedPlanId" aria-label="社保报价选择" class="plan-select"><el-option v-for="plan in proposals" :key="plan.id" :label="plan.name" :value="plan.id"/></el-select></div>
      <template v-if="activePlan">
        <div class="social-controls">
          <label><span>缴纳地</span><el-select v-model="activePlan.city" aria-label="社保缴纳地"><el-option v-for="city in CITY_POLICIES" :key="city.id" :label="city.name" :value="city.id"/></el-select></label>
          <label><span>基数工资来源</span><el-select v-model="activePlan.contributionMode" aria-label="基数工资来源"><el-option label="新员工：使用报价月薪" value="salary"/><el-option label="老员工：上年度月平均工资" value="priorYear"/></el-select></label>
          <label><span>{{activePlan.contributionMode==='salary'?'报价月薪（联动）':'上年度月平均工资'}}</span><div v-if="activePlan.contributionMode==='salary'" class="readonly-value">{{money(activePlan.basePay)}}</div><el-input-number v-else v-model="activePlan.priorYearPay" :min="0" :max="100000000" :precision="2" :controls="false" placeholder="待填写" aria-label="上年度月平均工资"/></label>
        </div>
        <div class="summary-strip"><div><span>个人月缴纳</span><strong>{{money(activeSocial?.employee)}}</strong></div><div><span>公司月成本</span><strong>{{money(activeSocial?.employer)}}</strong></div><div><span>双方月度合计</span><strong>{{money(activeSocial?.total)}}</strong></div></div>
        <p class="inline-note">{{activePolicy.name}}社保基数 {{money(activePolicy.socialMin)}}–{{money(activePolicy.socialMax)}}；公积金基数 {{money(activePolicy.housingMin)}}–{{money(activePolicy.housingMax)}} 元 / 月。比例和上下限只读。</p>
        <div v-if="!activeSocial" class="empty-state">请先填写{{activePlan.contributionMode==='salary'?'报价月薪':'上年度月平均工资'}}，系统会自动计算各险种金额。</div>
        <div v-else class="table-scroll"><table class="detail-table"><thead><tr><th>缴费项目</th><th>缴费基数</th><th>个人比例</th><th>个人金额 / 月</th><th>公司比例</th><th>公司金额 / 月</th></tr></thead><tbody><tr v-for="line in activeSocial.lines" :key="line.key"><th>{{line.name}}</th><td>{{line.base===null?'—':money(line.base)}}</td><td>{{line.employeeRate}}</td><td>{{money(line.employee)}}</td><td>{{line.employerRate}}</td><td>{{money(line.employer)}}</td></tr></tbody></table></div>
        <div v-if="activePlan.city==='SH'" class="policy-warning">上海补充公积金已去重：公司按公积金基数 × 8% 取整，仅计一份。汇总企业成本时先扣除年包中已包含的补充公积金，再加入实际公司缴费；普通公积金仍按 7% 计算。</div>
        <div class="panel-foot">个人养老、医疗、失业向上取 1 位小数；公司对应险种取 2 位小数；公积金取整数。原表未设置的项目按 0 参与合计，不代表已核实当前政策。</div>
      </template>
    </section>

    <section v-else-if="view==='rates'" class="panel">
      <div class="section-heading"><div><h3>各工作地的 Hourly / Daily Rate</h3><p>年包经补充公积金去重后加公司五险一金年成本，再按固定工时折算。用于 HR 内部成本测算。</p></div><el-radio-group v-model="rateUnit" size="small" aria-label="成本单位"><el-radio-button value="hourly">Hourly Rate</el-radio-button><el-radio-button value="daily">Daily Rate</el-radio-button></el-radio-group></div>
      <div class="rate-toolbar"><el-checkbox-group v-model="rateCities" aria-label="比较工作地"><el-checkbox v-for="city in CITY_POLICIES" :key="city.id" :value="city.id">{{city.name}}</el-checkbox></el-checkbox-group><div class="fixed-caption">1,880 小时 / 年 · 8 小时 / 天 · Overhead 169,200 元 / 年</div></div>
      <div class="compact-policy">北京按本地成本计算 · 上海补充公积金已去重 <button @click="notesOpen=true">查看口径</button></div>
      <div v-if="!rateCities.length" class="empty-state">请选择至少一个工作地进行比较。</div>
      <div v-else class="table-scroll"><table class="rate-table"><thead><tr><th>工作地</th><th v-for="plan in proposals" :key="plan.id">{{plan.name}}<small>年包 {{money(totalPackage(plan))}}</small></th></tr></thead><tbody>
        <tr v-for="city in selectedCities" :key="city.id"><th>{{city.name}}<small>{{rateUnit==='hourly'?'元 / 小时':'元 / 天'}}</small></th><td v-for="plan in proposals" :key="plan.id"><div class="rate-pair"><span>不含 Overhead<strong>{{money(rateFor(plan,city.id,false))}}</strong></span><span>含 Overhead<strong>{{money(rateFor(plan,city.id,true))}}</strong></span></div><div class="rate-detail">公司月缴费 {{money(contributions(city.id,contributionSalary(plan))?.employer)}}<span v-if="city.id==='SH'"> · 年包去重 {{money(plan.supplementary)}} / 年</span></div></td></tr>
      </tbody></table></div>
      <div class="panel-foot">缺少年包组成项或基数工资时显示“—”。各城市使用相同的手填年包比较；切换城市不会自动调整年包补充公积金或福利，请先在薪资方案中核对。</div>
    </section>

    <section v-else class="panel rules-panel">
      <div class="section-heading"><div><h3>原表固定规则</h3><p>灰色区域只读。原始来源为《薪资计算.xlsx》的“招聘工具”工作表。</p></div><el-icon><Lock /></el-icon></div>
      <div class="rule-grid"><div><span>年发薪月数</span><strong>12 个月</strong><small>B13:E13</small></div><div><span>报价年终奖</span><strong>月薪 × 2</strong><small>C15:E15，当前薪资可手填</small></div><div><span>年度工时</span><strong>1,880 小时</strong><small>C21:E30</small></div><div><span>年度 Overhead</span><strong>169,200 元</strong><small>C21:E30</small></div></div>
      <div class="table-scroll"><table class="detail-table"><thead><tr><th>工作地</th><th>社保基数范围</th><th>公积金基数范围</th><th>个人 / 公司公积金</th><th>来源</th></tr></thead><tbody><tr v-for="city in CITY_POLICIES" :key="city.id"><th>{{city.name}}</th><td>{{city.socialMin}}–{{city.socialMax}}</td><td>{{city.housingMin}}–{{city.housingMax}}</td><td>{{city.housingBp/100}}% / {{city.housingBp/100}}%</td><td>A{{city.row}}:AN{{city.row}}</td></tr></tbody></table></div>
      <el-button class="rules-explain" text @click="notesOpen=true">查看完整公式与口径说明</el-button>
      <div class="panel-foot">未提供个税、税后收入或更多城市的规则，暂不计算。当前页面不会保存谈薪记录或发送给候选人。</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import {computed,ref} from 'vue'
import {Plus,MoreFilled,Lock} from '@element-plus/icons-vue'
import {CITY_POLICIES,RULES,annualBonus,cityPolicy,contributions,contributionSalary,quotationRates,increaseRate,missingFields,totalPackage,type Amount,type CityId,type SalaryPlan} from '@/utils/salaryCalculator'
type InputKey='basePay'|'onsite'|'annualBonus'|'projectBonus'|'benefits'|'supplementary'
type RowKey=InputKey|'months'|'total'
const salaryRows:{key:RowKey;label:string;unit:string;hint?:string}[]=[
  {key:'basePay',label:'税前月薪',unit:'Base Pay · 元 / 月'},
  {key:'months',label:'年发薪月数',unit:'Salary Month'},
  {key:'onsite',label:'驻场津贴',unit:'Onsite Allowance · 元 / 年',hint:'原表直接加到年包，此处录入全年津贴总额。'},
  {key:'annualBonus',label:'年终奖',unit:'Annual Bonus · 元 / 年'},
  {key:'projectBonus',label:'项目奖金',unit:'Project Bonus · 元 / 年'},
  {key:'benefits',label:'年度福利',unit:'Yearly Benefits · 元 / 年',hint:'原表示例合计 5,800 元；需人工核对性别相关福利和销售电话费。'},
  {key:'supplementary',label:'年包补充公积金',unit:'Supplementary Housing Fund · 元 / 年',hint:'此项为年包手填金额，与公司缴费明细区分。原表上海示例为月薪 × 8% × 12；切换城市后请重新核对。'},
]
let nextId=1
function makePlan(isCurrent=false):SalaryPlan {const id=nextId++;return {id,name:isCurrent?'当前薪资':`报价 ${id-1}`,isCurrent,city:'SH',basePay:undefined,onsite:undefined,annualBonus:undefined,projectBonus:undefined,benefits:undefined,supplementary:undefined,contributionMode:'salary',priorYearPay:undefined,note:''}}
const plans=ref<SalaryPlan[]>([makePlan(true),makePlan(),makePlan(),makePlan()])
const contextOpen=ref(false),notesOpen=ref(false)
const view=ref('salary'),rateUnit=ref('hourly'),selectedPlanId=ref(plans.value[1].id),exampleLoaded=ref(false)
const rateCities=ref<CityId[]>(CITY_POLICIES.map(c=>c.id)),context=ref({candidate:'',pe:'',title:'',onboard:''})
const proposals=computed(()=>plans.value.filter(p=>!p.isCurrent)),currentTotal=computed(()=>totalPackage(plans.value[0]))
const activePlan=computed(()=>proposals.value.find(p=>p.id===selectedPlanId.value)??proposals.value[0])
const activePolicy=computed(()=>cityPolicy(activePlan.value.city))
const activeSocial=computed(()=>contributions(activePlan.value.city,contributionSalary(activePlan.value)))
const selectedCities=computed(()=>CITY_POLICIES.filter(c=>rateCities.value.includes(c.id)))
const money=(value:Amount)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2}):'—'
const percent=(value:Amount)=>typeof value==='number'?`${(value*100).toFixed(2)}%`:'—'
const isLocked=(key:RowKey,p:SalaryPlan)=>key==='months'||key==='total'||(key==='annualBonus'&&!p.isCurrent)
function cellValue(key:RowKey,p:SalaryPlan){return key==='months'?String(RULES.salaryMonths):money(key==='total'?totalPackage(p):annualBonus(p))}
function addPlan(){plans.value.push(makePlan());view.value='salary'}
function planAction(cmd:string,plan:SalaryPlan){if(cmd==='copy')plans.value.push({...plan,id:nextId++,name:`${plan.name} 副本`.slice(0,30)});if(cmd==='remove'&&proposals.value.length>1){plans.value=plans.value.filter(p=>p.id!==plan.id);if(selectedPlanId.value===plan.id)selectedPlanId.value=proposals.value[0].id}}
function clearPlans(){nextId=1;plans.value=[makePlan(true),makePlan(),makePlan(),makePlan()];selectedPlanId.value=plans.value[1].id;exampleLoaded.value=false}
function loadExample(){clearPlans();const samples=[[18000,0,54000,0,21600,0],[20000,0,40000,0,5800,19200],[25000,0,50000,0,5800,0],[30000,0,60000,0,5800,0]];plans.value.forEach((p,i)=>{[p.basePay,p.onsite,p.annualBonus,p.projectBonus,p.benefits,p.supplementary]=samples[i]});exampleLoaded.value=true;view.value='salary'}
function rateFor(plan:SalaryPlan,city:CityId,overhead:boolean){
  const result=quotationRates(plan,city)
  if(!result)return undefined
  return rateUnit.value==='daily'?(overhead?result.dailyWithOverhead:result.daily):(overhead?result.hourlyWithOverhead:result.hourly)
}
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
