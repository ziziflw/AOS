// Adapted from shadcn/ui Kbd, MIT. See docs/licenses/shadcn-ui.txt.
import type { ComponentProps } from 'react'
export function Kbd({ className = '', ...props }: ComponentProps<'kbd'>) {
  return <kbd data-slot="kbd" className={`studio-kbd ${className}`} {...props} />
}
