import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { ExternalLink, X } from "lucide-react";
import type { NavLeg } from "../lib/types";

interface Props {
  url: string;
  leg: NavLeg;
  onClose: () => void;
}

// 电脑上没有百度地图 App：给出本页二维码，手机扫码后在手机上点按钮唤起
export default function ScanModal({ url, leg, onClose }: Props) {
  const [img, setImg] = useState("");
  const isLocal = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);

  useEffect(() => {
    QRCode.toDataURL(url, { width: 240, margin: 1 }).then(setImg).catch(() => setImg(""));
  }, [url]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-6 text-center shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-lg font-bold">用手机扫码打开</h3>
          <button onClick={onClose} className="text-[#717171] hover:text-[#222]" aria-label="关闭">
            <X size={20} />
          </button>
        </div>
        <p className="text-sm text-[#717171]">
          电脑上没有百度地图 App。用手机相机扫码打开本页，再点「在百度地图打开」即可带上全部途经点。
        </p>
        {img && <img src={img} alt="本页二维码" className="mx-auto my-4 h-60 w-60" />}
        {isLocal && (
          <p className="mb-3 rounded-lg bg-[#FFF7ED] px-3 py-2 text-xs text-[#C2410C]">
            当前是 localhost 地址，手机扫了打不开。请用电脑的局域网地址（如 http://192.168.x.x:端口）打开本页后再扫码。
          </p>
        )}
        <p className="break-all text-xs text-[#B0B0B0]">{url}</p>

        <div className="mt-5 border-t border-[#EBEBEB] pt-4">
          <a
            href={leg.web_uri}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-xl border border-[#DDDDDD] px-4 py-2 text-sm font-medium text-[#222] transition hover:border-[#B0B0B0]"
          >
            <ExternalLink size={14} />
            在网页版百度地图查看{leg.via.length ? `（含 ${leg.via.length} 个途经点）` : ""}
          </a>
          {leg.via.length > 0 && (
            <p className="mt-2 text-xs text-[#717171]">
              打不开或路线不对？
              <a
                href={leg.web_basic_uri}
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-2 hover:text-[#222]"
              >
                改用只含起终点的网页版
              </a>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
