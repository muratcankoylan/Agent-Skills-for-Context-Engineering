export const primaryNavigation = [
  { href: "/", label: "Overview", index: "01" },
  { href: "/runs", label: "Runs", index: "02" },
  { href: "/review", label: "Review queue", index: "03" },
  { href: "/artifacts", label: "Artifacts", index: "04" },
  { href: "/deployment", label: "Deployment", index: "05" },
  { href: "/observations", label: "Local observations", index: "06" },
  { href: "/service", label: "Research service", index: "07" },
] as const;

export function isCurrentRoute(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
