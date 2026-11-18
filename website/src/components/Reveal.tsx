import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'motion/react';

interface Props {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: 'div' | 'section' | 'li';
}

export default function Reveal({ children, delay = 0, className = '', as = 'div' }: Props) {
  const reduced = useReducedMotion();
  const Tag = motion[as];
  return (
    <Tag
      className={className}
      initial={reduced ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: reduced ? 0 : 0.4, delay: reduced ? 0 : delay, ease: 'easeOut' }}
    >
      {children}
    </Tag>
  );
}
