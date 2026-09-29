"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isCurrentRoute, primaryNavigation } from "../lib/navigation.ts";

export function PrimaryNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary navigation">
      <p className="nav-label">Control plane</p>
      <ul className="nav-list">
        {primaryNavigation.map((item) => {
          const isCurrent = isCurrentRoute(pathname, item.href);
          return (
            <li key={item.href}>
              <Link href={item.href} aria-current={isCurrent ? "page" : undefined}>
                <span aria-hidden="true">{item.index}</span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
