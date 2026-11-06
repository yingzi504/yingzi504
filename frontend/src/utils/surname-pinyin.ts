/**
 * 常见中文姓氏 → 拼音映射
 * 覆盖《百家姓》及常见姓氏，约 150+ 覆盖 90%+ 场景
 */
const SURNAME_PINYIN: Record<string, string> = {
  '王': 'Wang', '李': 'Li', '张': 'Zhang', '刘': 'Liu', '陈': 'Chen',
  '杨': 'Yang', '赵': 'Zhao', '黄': 'Huang', '周': 'Zhou', '吴': 'Wu',
  '徐': 'Xu', '孙': 'Sun', '胡': 'Hu', '朱': 'Zhu', '高': 'Gao',
  '林': 'Lin', '何': 'He', '郭': 'Guo', '马': 'Ma', '罗': 'Luo',
  '梁': 'Liang', '宋': 'Song', '郑': 'Zheng', '谢': 'Xie', '韩': 'Han',
  '唐': 'Tang', '冯': 'Feng', '于': 'Yu', '董': 'Dong', '萧': 'Xiao',
  '程': 'Cheng', '曹': 'Cao', '袁': 'Yuan', '邓': 'Deng', '许': 'Xu',
  '傅': 'Fu', '沈': 'Shen', '曾': 'Zeng', '彭': 'Peng', '吕': 'Lyu',
  '苏': 'Su', '卢': 'Lu', '蒋': 'Jiang', '蔡': 'Cai', '贾': 'Jia',
  '丁': 'Ding', '魏': 'Wei', '薛': 'Xue', '叶': 'Ye', '阎': 'Yan',
  '余': 'Yu', '潘': 'Pan', '杜': 'Du', '戴': 'Dai', '夏': 'Xia',
  '钟': 'Zhong', '汪': 'Wang', '田': 'Tian', '任': 'Ren', '姜': 'Jiang',
  '范': 'Fan', '方': 'Fang', '石': 'Shi', '姚': 'Yao', '谭': 'Tan',
  '廖': 'Liao', '邹': 'Zou', '熊': 'Xiong', '金': 'Jin', '陆': 'Lu',
  '郝': 'Hao', '孔': 'Kong', '白': 'Bai', '崔': 'Cui', '康': 'Kang',
  '毛': 'Mao', '邱': 'Qiu', '秦': 'Qin', '江': 'Jiang', '史': 'Shi',
  '顾': 'Gu', '侯': 'Hou', '邵': 'Shao', '孟': 'Meng', '龙': 'Long',
  '万': 'Wan', '段': 'Duan', '钱': 'Qian', '汤': 'Tang', '尹': 'Yin',
  '黎': 'Li', '易': 'Yi', '常': 'Chang', '武': 'Wu', '乔': 'Qiao',
  '贺': 'He', '赖': 'Lai', '龚': 'Gong', '文': 'Wen', '庞': 'Pang',
  '樊': 'Fan', '殷': 'Yin', '施': 'Shi', '陶': 'Tao', '洪': 'Hong',
  '翟': 'Zhai', '安': 'An', '颜': 'Yan', '倪': 'Ni', '严': 'Yan',
  '牛': 'Niu', '温': 'Wen', '芦': 'Lu', '季': 'Ji', '俞': 'Yu',
  '鲁': 'Lu', '葛': 'Ge', '伍': 'Wu', '申': 'Shen', '尤': 'You',
  '毕': 'Bi', '聂': 'Nie', '焦': 'Jiao', '向': 'Xiang', '柳': 'Liu',
  '邢': 'Xing', '路': 'Lu', '岳': 'Yue', '齐': 'Qi',
  '肖': 'Xiao', '付': 'Fu', '苗': 'Miao',
}

/**
 * 将中文敬称格式（王先生/李女士）转换为英文格式（Mr. Wang / Ms. Li）
 * 如果不是中文敬称格式，返回原始名称
 *
 * @param name 原始名称（如 "王先生"、"李女士"、"Mr. Wang"）
 * @returns 本地化后的名称
 */
export function localizeChineseHonorific(name: string): string {
  // 如果已经是英文格式（包含 Mr./Ms.）则不处理
  if (/^Mr\.?\s|^Ms\.?\s|^Mrs\.?\s/i.test(name)) {
    return name
  }

  // 匹配中文敬称：X先生 / X女士
  const match = name.match(/^([\u4e00-\u9fff])(先生|女士)$/)
  if (!match) {
    return name
  }

  const surname = match[1]    // 姓氏汉字
  const suffix = match[2]     // 先生 或 女士
  const pinyin = SURNAME_PINYIN[surname]

  if (!pinyin) {
    // 如果姓氏不在映射表中，返回原始名称
    return name
  }

  const title = suffix === '女士' ? 'Ms.' : 'Mr.'
  return `${title} ${pinyin}`
}
