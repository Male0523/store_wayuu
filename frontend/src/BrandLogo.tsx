type BrandLogoProps = {
  variant: 'full' | 'icon'
  alt?: string
  className?: string
}

const logoSources = {
  full: '/images/logo-wayuu.svg',
  icon: '/images/isotipo-wayuu.svg',
} as const

export default function BrandLogo({ variant, alt, className = '' }: BrandLogoProps) {
  const accessibleName = alt ?? (variant === 'full' ? 'Tienda Wayúu' : 'Isotipo de Tienda Wayúu')

  return (
    <img
      src={logoSources[variant]}
      alt={accessibleName}
      className={`object-contain ${className}`.trim()}
    />
  )
}
