import * as React from "react"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, value, onChange, ...props }, ref) => {
    return (
      <div className="relative">
        <input
          type={type}
          className={cn(
            "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
            className
          )}
          ref={ref}
          value={value}
          onChange={onChange}
          {...props}
        />
        {value && (
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-300 hover:text-white p-1 rounded-md hover:bg-slate-600 transition-colors"
            style={{ backgroundColor: 'rgba(38, 50, 70, 1)' }}
            onClick={() => onChange?.({ target: { value: "" } } as React.ChangeEvent<HTMLInputElement>)}
          >
            <X className="h-5 w-5" style={{ color: 'white' }} />
          </button>
        )}
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }
