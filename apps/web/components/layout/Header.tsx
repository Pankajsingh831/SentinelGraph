export function Header({ title }: { title: string }) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-950/50 px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-white">{title}</h1>
      </div>
      <div className="flex items-center gap-4">
        <div className="h-8 w-64 rounded-md bg-slate-900 border border-slate-800 px-3 py-1 text-sm text-slate-400 flex items-center">
          Search...
        </div>
        <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center text-sm font-medium text-slate-300">
          U
        </div>
      </div>
    </header>
  );
}
