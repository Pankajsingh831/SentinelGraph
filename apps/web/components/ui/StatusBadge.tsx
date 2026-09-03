import React from 'react';

type CaseStatus = 'OPEN' | 'ESCALATED' | 'RESOLVED' | 'CLOSED' | string;

interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: CaseStatus;
}

export function StatusBadge({ status, className = '', ...props }: StatusBadgeProps) {
  const baseClasses = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold";
  
  const upperStatus = status.toUpperCase();
  let colorClass = "bg-gray-100 text-gray-800"; // default

  if (upperStatus === 'OPEN') colorClass = "bg-blue-100 text-blue-800";
  else if (upperStatus === 'ESCALATED') colorClass = "bg-orange-100 text-orange-800";
  else if (upperStatus === 'RESOLVED') colorClass = "bg-green-100 text-green-800";
  else if (upperStatus === 'CLOSED') colorClass = "bg-gray-100 text-gray-800";

  return (
    <span className={`${baseClasses} ${colorClass} ${className}`} {...props}>
      {upperStatus}
    </span>
  );
}
