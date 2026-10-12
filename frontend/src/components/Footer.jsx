const YEAR = new Date().getFullYear()

const FOOTER_LINKS = [
  { label: 'Privacy Policy', href: '#privacy' },
  { label: 'Terms of Use', href: '#terms' },
  { label: 'Accessibility', href: '#accessibility' },
]

export default function Footer() {
  return (
    <footer className="bg-[#123a5c] text-white">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-3 px-4 py-4 text-sm sm:flex-row sm:justify-between sm:px-6 lg:px-8">
        <p className="text-white/90">
          Smart Port Management System &copy; {YEAR} All rights reserved.
        </p>

        <nav className="flex items-center gap-3 text-white/90">
          {FOOTER_LINKS.map((link, i) => (
            <span key={link.label} className="flex items-center gap-3">
              <a href={link.href} className="font-medium hover:text-white">
                {link.label}
              </a>
              {i < FOOTER_LINKS.length - 1 && (
                <span className="text-white/30">|</span>
              )}
            </span>
          ))}
        </nav>

        <div className="flex items-center gap-2 font-medium text-green-400">
          <span className="h-2 w-2 rounded-full bg-green-400" />
          System Status: Operational
        </div>
      </div>
    </footer>
  )
}
