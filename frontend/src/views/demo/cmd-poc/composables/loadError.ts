/**
 * 把各类请求失败归一到一句可读的中文提示，供列表 / 指标的错误条展示。
 *
 * 背景：网关 502、后端重启、隧道抖动时，axios 抛出的多是技术性文案
 * （"Request failed with status code 502"）。此前各面板用 `catch {}` 静默吞掉，
 * 页面只剩「暂无数据 / 0 条」——用户会把「取不到」读成「没有」，
 * 进而错判成「我的提交没生效」（复测报告 BUG-01 的观感来源）。
 *
 * @param error  捕获到的异常
 * @param action 动作名，用于拼成「客户主档加载失败：…」
 */
export function describeError(error: unknown, action = '数据加载'): string {
  const raw = error instanceof Error ? error.message : String(error ?? '');
  if (/502|Bad Gateway/i.test(raw)) {
    return `${action}失败：网关 502，后端服务当前不可达或正在重启 —— 请稍后点「重新加载」，或联系管理员确认服务状态`;
  }
  if (/504|Gateway Time-?out/i.test(raw)) {
    return `${action}失败：网关超时（504），后端响应过慢`;
  }
  if (/Network Error|ERR_CONNECTION|ECONNREFUSED|Failed to fetch/i.test(raw)) {
    return `${action}失败：无法连接后端服务`;
  }
  if (/timeout|超时/i.test(raw)) {
    return `${action}失败：请求超时`;
  }
  if (/401|登录态|token/i.test(raw)) {
    return `${action}失败：登录态已失效，请重新登录`;
  }
  return `${action}失败：${raw || '未知错误'}`;
}
