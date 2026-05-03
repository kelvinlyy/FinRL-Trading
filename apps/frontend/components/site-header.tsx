import Link from "next/link";

const nav = [
  { href: "/", label: "Home" },
  { href: "/results", label: "Results" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-lead/30 bg-deep-space/85 backdrop-blur">
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-5">
        <Link href="/" className="font-display text-[21px] font-[480] tracking-[0.02em] text-starlight">
          FinRL-X
        </Link>
        <nav className="flex items-center gap-2">
          {nav.map((item) => (
            <Link key={item.href} href={item.href} className="rounded-[40px] px-5 py-2 text-sm text-silver transition hover:bg-ghost-blue/10 hover:text-starlight">
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
