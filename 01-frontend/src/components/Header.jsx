export default function Header() {
  return (
    <header className="bg-slate-800 border-b border-slate-700 p-4 mb-8 sticky top-0 z-10">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center font-bold text-white">
            А
          </div>
          <span className="text-xl font-bold text-white">Альфа-Инсайт</span>
        </div>
        
        <div className="flex gap-3 w-full md:w-auto">
          <select className="bg-slate-900 text-slate-200 border border-slate-600 rounded px-3 py-2 text-sm outline-none w-full md:w-auto cursor-pointer">
            <option>ООО "Ромашка" (МСП)</option>
            <option>АО "Вектор" (Крупный бизнес)</option>
          </select>
          
          <select className="bg-slate-900 text-slate-200 border border-slate-600 rounded px-3 py-2 text-sm outline-none w-full md:w-auto cursor-pointer">
            <option>CEO / Собственник</option>
            <option>CFO / Казначей</option>
            <option>Главный бухгалтер</option>
          </select>
        </div>
      </div>
    </header>
  )
}