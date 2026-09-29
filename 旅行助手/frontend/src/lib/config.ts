// 浏览器端 AK（JSAPI GL 内嵌地图用，靠 Referer 白名单防盗用），从 frontend/.env.local 读取。
// 留空时，前端自动用后端静态地图兜底；填上后切成可交互 JSAPI GL 地图。
export const BAIDU_JSAPI_AK: string = import.meta.env.VITE_BAIDU_BROWSER_AK ?? "";
