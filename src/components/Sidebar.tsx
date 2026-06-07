"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Dashboard", icon: "▣" },
  { href: "/pipeline", label: "Investor Pipeline", icon: "≡" },
  { href: "/capture", label: "Lead Capture", icon: "✦" },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col bg-ink-900 text-slate-300">
      <div className="px-5 py-5 border-b border-white/10">
        <div className="text-white font-semibold text-lg leading-tight">ProperInvest</div>
        <div className="text-brand-300 text-xs tracking-wide uppercase">CRM</div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-brand-600 text-white"
                  : "hover:bg-white/5 hover:text-white"
              }`}
            >
              <span className="w-5 text-center opacity-80">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-4 border-t border-white/10 text-xs text-slate-500">
        <div className="text-slate-400">Module 1 of 6</div>
        <div className="mt-1">Investor Leads · live</div>
      </div>
    </aside>
  );
}
