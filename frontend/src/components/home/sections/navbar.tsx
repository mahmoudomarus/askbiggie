'use client';

import { Icons } from '@/components/home/icons';
import { NavMenu } from '@/components/home/nav-menu';
import { siteConfig } from '@/lib/home';
import { cn } from '@/lib/utils';
import { Menu, X, Github } from 'lucide-react';
import { AnimatePresence, motion, useScroll } from 'motion/react';
import Link from 'next/link';
import Image from 'next/image';
import { useEffect, useState } from 'react';
import { useAuth } from '@/components/AuthProvider';

const INITIAL_WIDTH = '70rem';
const MAX_WIDTH = '800px';

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const drawerVariants = {
  hidden: { opacity: 0, y: 100 },
  visible: {
    opacity: 1,
    y: 0,
    rotate: 0,
    transition: {
      type: 'spring',
      damping: 15,
      stiffness: 200,
      staggerChildren: 0.03,
    },
  },
  exit: {
    opacity: 0,
    y: 100,
    transition: { duration: 0.1 },
  },
};

const drawerMenuContainerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const drawerMenuVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export function Navbar() {
  const { scrollY } = useScroll();
  const [hasScrolled, setHasScrolled] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('hero');
  const { user } = useAuth();

  useEffect(() => {
    // Skip if no navigation items
    if (siteConfig.nav.links.length === 0) return;

    const handleScroll = () => {
      const sections = siteConfig.nav.links.map((item) =>
        item.href.substring(1),
      );

      for (const section of sections) {
        const element = document.getElementById(section);
        if (element) {
          const rect = element.getBoundingClientRect();
          if (rect.top <= 150 && rect.bottom >= 150) {
            setActiveSection(section);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const unsubscribe = scrollY.on('change', (latest) => {
      setHasScrolled(latest > 10);
    });
    return unsubscribe;
  }, [scrollY]);

  const toggleDrawer = () => setIsDrawerOpen((prev) => !prev);
  const handleOverlayClick = () => setIsDrawerOpen(false);

  return (
    <header
      className={cn(
        'sticky z-50 mx-4 flex justify-center transition-all duration-300 md:mx-0',
        hasScrolled ? 'top-6' : 'top-4 mx-0',
      )}
    >
      <motion.div
        initial={{ width: INITIAL_WIDTH }}
        animate={{ width: hasScrolled ? MAX_WIDTH : INITIAL_WIDTH }}
        transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div
          className={cn(
            'mx-auto max-w-7xl rounded-2xl transition-all duration-300  xl:px-0',
            hasScrolled
              ? 'px-2 border border-border backdrop-blur-lg bg-background/75'
              : 'shadow-none px-7',
          )}
        >
          <div className="flex h-[56px] items-center justify-between p-4">
            <Link href="/" className="flex items-center gap-3">
              <Image
                src="https://bignoodle.com/askbiggie/bignoodle_header_logo.png"
                alt="Bignoodle AI Logo"
                width={80}
                height={16}
                priority
              /> 
            </Link>

            <NavMenu />

            <div className="flex flex-row items-center gap-1 md:gap-3 shrink-0">
              <div className="flex items-center space-x-3">
                {user ? (
                  <Link
                    className="bg-secondary h-8 hidden md:flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-secondary-foreground w-fit px-4 shadow-sm border border-border"
                    href="/dashboard"
                  >
                    Dashboard
                  </Link>
                ) : (
                  <Link
                    className="bg-secondary h-8 hidden md:flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-secondary-foreground w-fit px-4 shadow-sm border border-border"
                    href="/auth"
                  >
                    Get started
                  </Link>
                )}
              </div>

              <Menu
                className="size-6 cursor-pointer md:hidden"
                onClick={toggleDrawer}
              />
            </div>
          </div>
        </div>
      </motion.div>

      <AnimatePresence>
        {isDrawerOpen && (
          <>
            <motion.div
              className="fixed inset-0 bg-background/40 backdrop-blur-md z-40"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={overlayVariants}
              onClick={handleOverlayClick}
            />

            <motion.div
              className="fixed inset-x-0 w-[95%] mx-auto bottom-3 bg-background border border-border p-4 rounded-xl shadow-lg z-50"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={drawerVariants}
            >
              {/* Mobile menu content */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <Link href="/" className="flex items-center gap-3">
                    <Image
                      src="https://bignoodle.com/askbiggie/bignoodle_header_logo.png"
                      alt="Bignoodle AI Logo"
                      width={70}
                      height={14}
                      priority
                    />
                    <span className="font-medium text-primary text-sm">
                      / Biggie
                    </span>
                  </Link>
                  <button
                    onClick={toggleDrawer}
                    className="border border-border rounded-md p-1 cursor-pointer"
                  >
                    <X className="size-5" />
                  </button>
                </div>

                <motion.ul
                  className="flex flex-col text-sm mb-4 border border-border rounded-md"
                  variants={drawerMenuContainerVariants}
                >
                  <AnimatePresence>
                    {siteConfig.nav.links.length > 0 && siteConfig.nav.links.map((item) => (
                      <motion.li
                        key={item.id}
                        className="p-2.5 border-b border-border last:border-b-0"
                        variants={drawerMenuVariants}
                      >
                        <a
                          href={item.href}
                          onClick={(e) => {
                            e.preventDefault();
                            const element = document.getElementById(
                              item.href.substring(1),
                            );
                            if (element) {
                              element.scrollIntoView({
                                behavior: 'smooth',
                              });
                            setIsDrawerOpen(false);
                            }
                          }}
                          className="font-normal text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {item.name}
                        </a>
                      </motion.li>
                    ))}
                  </AnimatePresence>
                </motion.ul>

                <div className="flex flex-col gap-2">
                  {user ? (
                    <Link
                      className="bg-secondary flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-secondary-foreground h-10 w-full px-4 shadow-sm border border-border"
                      href="/dashboard"
                    >
                      Dashboard
                    </Link>
                  ) : (
                    <Link
                      className="bg-secondary flex items-center justify-center text-sm font-normal tracking-wide rounded-full text-secondary-foreground h-10 w-full px-4 shadow-sm border border-border"
                      href="/auth"
                    >
                      Get started
                    </Link>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </header>
  ); 
}
