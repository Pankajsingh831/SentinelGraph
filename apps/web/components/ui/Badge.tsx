import React from 'react';

type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tier: RiskTier;
}

export function Badge({ tier, className = '', ...props }: BadgeProps) {
  const baseClasses = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold";
  
  const colors = {
    LOW: "bg-green-100 text-green-800",
    MEDIUM: "bg-yellow-100 text-yellow-800",
    HIGH: "bg-orange-100 text-orange-800",
    CRITICAL: "bg-red-100 text-red-800"
  };

  return (
    <span className={`${baseClasses} ${colors[tier]} ${className}`} {...props}>
      {tier}
    </span>
  );
}
