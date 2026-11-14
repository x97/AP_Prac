"use client";

import { usePathname, useRouter } from "next/navigation";
import type { AnchorHTMLAttributes, ReactNode } from "react";

type QuietLinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  href: string;
  children: ReactNode;
  prefetchOnHover?: boolean;
};

/**
 * An internal link that does not join the initial route-prefetch burst.
 *
 * Next Link prefetches every mounted route in the current implementation. The
 * app shell renders a large desktop sidebar plus a mobile tabbar, so those
 * prefetches are duplicated. This component keeps client-side navigation but
 * only prefetches after the user shows intent with hover/focus.
 */
export function QuietLink({
  href,
  children,
  prefetchOnHover = true,
  onClick,
  onMouseEnter,
  onFocus,
  ...props
}: QuietLinkProps) {
  const router = useRouter();
  const pathname = usePathname();

  const prefetch = () => {
    if (prefetchOnHover && href !== pathname) void router.prefetch(href);
  };

  return (
    <a
      {...props}
      href={href}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        if (props.target && props.target !== "_self") return;
        event.preventDefault();
        if (href !== pathname) router.push(href);
      }}
      onMouseEnter={(event) => {
        onMouseEnter?.(event);
        prefetch();
      }}
      onFocus={(event) => {
        onFocus?.(event);
        prefetch();
      }}
    >
      {children}
    </a>
  );
}
