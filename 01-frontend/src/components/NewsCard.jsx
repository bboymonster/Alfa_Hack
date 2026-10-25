export default function NewsCard() {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 mb-6 max-w-4xl shadow-lg">
      
      <div className="flex gap-3 text-xs text-slate-400 mb-4 items-center flex-wrap">
        <span className="bg-blue-900/50 text-blue-300 px-2 py-1 rounded font-medium">Событие</span>
        <span>РБК</span>
        <span>•</span>
        <span>12 Октября</span>
        <span className="bg-slate-700 text-slate-300 px-2 py-1 rounded ml-auto">Металлургия</span>
      </div>
      
      <h2 className="text-xl font-semibold text-white mb-4">
        Крупный поставщик металлов объявил о повышении цен на 15%
      </h2>
      
      <div className="bg-slate-900/60 rounded-lg p-5 mb-5 border border-slate-700/50">
        <h3 className="text-sm font-bold text-purple-400 mb-2">Почему это важно для вашей компании:</h3>
        <p className="text-slate-300 text-sm mb-4 leading-relaxed">
          Ваша компания закупает металлы у данного поставщика. Рост цен может увеличить себестоимость продукции на 3-5%. Рекомендуется рассмотреть альтернативных поставщиков или зафиксировать цены по текущим контрактам.
        </p>
        
        <div className="flex flex-wrap gap-2 mt-4">
          <span className="text-xs border border-green-500/50 text-green-400 px-2 py-1 rounded bg-green-500/10">[Факт]</span>
          <span className="text-xs border border-blue-500/50 text-blue-400 px-2 py-1 rounded bg-blue-500/10">[Позиция Банка]</span>
          <span className="text-xs border border-purple-500/50 text-purple-400 px-2 py-1 rounded bg-purple-500/10">[Вывод AI]</span>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-6">
        <button className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer">
          Спросить нейросеть
        </button>
        <button className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer">
          В закладки
        </button>
      </div>
    </div>
  )
}