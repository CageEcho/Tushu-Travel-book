import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { BAIDU_JSAPI_AK } from "./lib/config";

if (BAIDU_JSAPI_AK) {
  const script = document.createElement("script");
  script.src = `https://api.map.baidu.com/api?type=webgl&v=1.0&ak=${encodeURIComponent(BAIDU_JSAPI_AK)}`;
  script.async = true;
  document.head.appendChild(script);
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
