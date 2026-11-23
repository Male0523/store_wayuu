type BrandLogoProps = {
  variant: 'full' | 'icon'
  monochrome?: boolean
  alt?: string
  className?: string
}

const logoSources = {
  full: {
    color: '/images/logo-wayuu.svg',
    monochrome: '/images/logotipo-wayuu-blanco.svg',
  },
  icon: {
    color: '/images/isotipo-wayuu.svg',
    monochrome: '/images/isotipo-wayuu-blanco.svg',
  },
} as const

export default function BrandLogo({ variant, monochrome = false, alt, className = '' }: BrandLogoProps) {
  const accessibleName = alt ?? (variant === 'full' ? 'Tienda Wayúu' : 'Isotipo de Tienda Wayúu')

  return (
    <img
      src={logoSources[variant][monochrome ? 'monochrome' : 'color']}
      alt={accessibleName}
      className={`object-contain ${className}`.trim()}
    />
  )
}
