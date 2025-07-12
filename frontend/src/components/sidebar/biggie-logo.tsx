'use client';

import Image from 'next/image';

interface BiggieLogoProps {
  size?: number;
}

export function BiggieLogoComponent({ size = 20 }: BiggieLogoProps) {
  return (
    <Image
      src="/logo.png"
      alt="Bignoodle AI"
      width={size}
      height={size * 0.7} // Maintain aspect ratio
      className="flex-shrink-0"
    />
  );
}
