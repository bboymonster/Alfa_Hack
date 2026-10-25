// Автономные демо-данные: зеркалят 02-backend/app/store.py (MemoryStore) и
// 02-backend/app/mock_ai.py. Используются, когда backend недоступен (например,
// статическая сборка на GitHub Pages), чтобы интерфейс оставался интерактивным.

export const ROLES = {
  CEO: 'CEO / Собственник',
  CFO: 'CFO / Казначей',
  ACCOUNTANT: 'Главный бухгалтер',
}

export const DEMO_COMPANIES = [
  {
    synthetic_u: 'U_1595',
    name: 'ООО «Модный Стиль Ритейл»',
    mainokved_code: '47.71',
    mainokved_name: 'Розничная торговля одеждой',
    revenue_company: 16461800000,
    cl_product_loa_mark: true,
    fts_flag: true,
    city: 'Москва',
    region: 'Москва',
  },
  {
    synthetic_u: 'U_1465',
    name: 'АО «Премиум Напитки Импорт»',
    mainokved_code: '46.34',
    mainokved_name: 'Оптовая торговля напитками',
    revenue_company: 44401190000,
    cl_product_loa_mark: true,
    fts_flag: true,
    city: 'Москва',
    region: 'Москва',
  },
  {
    synthetic_u: 'DEMO_LOCAL',
    name: 'ООО «Демо Локальный Сервис»',
    mainokved_code: '62.01',
    mainokved_name: 'Разработка программного обеспечения',
    revenue_company: 240000000,
    cl_product_loa_mark: false,
    fts_flag: false,
    city: 'Казань',
    region: 'Республика Татарстан',
  },
]

export const DEMO_NEWS = [
  {
    id: 'demo/news/financing',
    title: 'Демо: изменение стоимости заимствований',
    summary_facts: 'Учебный сценарий: стоимость новых кредитов изменилась.',
    source: 'Демонстрационные данные команды',
    source_url: null,
    published_at: '2026-09-11T13:30:00+00:00',
    category: 'Финансы и макроэкономика',
  },
  {
    id: 'demo/news/logistics',
    title: 'Демо: увеличение сроков международных поставок',
    summary_facts: 'Учебный сценарий: срок доставки по одному из маршрутов вырос.',
    source: 'Демонстрационные данные команды',
    source_url: null,
    published_at: '2026-09-10T09:00:00+00:00',
    category: 'Логистика',
  },
  {
    id: 'demo/news/reporting',
    title: 'Демо: обновление требований к отчётности',
    summary_facts: 'Учебный сценарий: предложено изменение формы отчётности.',
    source: 'Демонстрационные данные команды',
    source_url: null,
    published_at: '2026-09-09T10:00:00+00:00',
    category: 'Регулирование',
  },
]

const ROLE_FOCUS = {
  CEO: 'рынки сбыта и устойчивость бизнеса',
  CFO: 'денежный поток и стоимость финансирования',
  ACCOUNTANT: 'документы, учёт и сроки обязательств',
}

function generateInsight(news, company, role) {
  let impact, risks, features, action
  if (news.category === 'Финансы и макроэкономика') {
    if (company.cl_product_loa_mark) {
      impact = 'есть кредитные продукты: стоит проверить условия обслуживания долга'
      risks = ['В демонстрационном сценарии расходы на заёмные средства могут вырасти.']
    } else {
      impact = 'нет кредитных продуктов: прямой эффект на обслуживание долга не показан'
      risks = ['В демонстрационном сценарии изменение ставок может затронуть контрагентов.']
    }
    features = ['CL_PRODUCT_LOA_MARK', 'REVENUE_COMPANY']
    action = 'Сравнить сценарии денежных потоков и обсудить их с финансовой командой.'
  } else if (news.category === 'Логистика') {
    if (company.fts_flag) {
      impact = 'есть внешнеторговая деятельность: возможны изменения сроков поставок'
      risks = ['В демонстрационном сценарии импортная поставка может задержаться.']
    } else {
      impact = 'нет признака внешнеторговой деятельности: проверить косвенные зависимости'
      risks = ['В демонстрационном сценарии задержка возможна у поставщика компании.']
    }
    features = ['FTS_FLAG', 'MAINOKVED_CODE']
    action = 'Проверить сроки ближайших поставок и наличие альтернативных поставщиков.'
  } else {
    impact = 'изменение отчётности требует проверки применимости к вашей отрасли'
    risks = ['В демонстрационном сценарии могут потребоваться изменения документов.']
    features = ['MAINOKVED_CODE', 'REGION']
    action = 'Передать сообщение ответственному за учёт и проверить первоисточник.'
  }
  return {
    why_it_matters: `Демо: для ${company.name} (${company.synthetic_u}) ${impact}. Фокус роли ${role}: ${ROLE_FOCUS[role]}.`,
    risks,
    opportunities: [`Заранее оценить влияние на ${ROLE_FOCUS[role]} компании.`],
    action_item: `Демо-рекомендация для ${role}: ${action}`,
    alfa_bank_position: null,
    alfa_report_name: null,
    alfa_report_page: null,
    alfa_report_url: null,
    traceability: { matched_company_features: features, verified_sources: [] },
    agent_steps: null,
    self_check: null,
    confidence: null,
    mode: null,
  }
}

export function buildDemoFeed() {
  const feed = []
  for (const company of DEMO_COMPANIES) {
    for (const role of Object.keys(ROLES)) {
      DEMO_NEWS.forEach((news, index) => {
        let score = 9 - index
        if (role === 'ACCOUNTANT' && news.category === 'Регулирование') score = 10
        feed.push({
          id: `demo/insight/${company.synthetic_u}/${role}/${news.id}`,
          company_id: company.synthetic_u,
          role,
          news,
          insight: generateInsight(news, company, role),
          importance_score: score,
          is_favorite: false,
          is_demo: true,
        })
      })
    }
  }
  return feed
}

export function demoUser(email) {
  return {
    id: 'demo/user',
    email,
    full_name: `Демо ${email}`,
    role: 'CEO',
    current_company_id: 'U_1595',
    allowed_company_ids: DEMO_COMPANIES.map((c) => c.synthetic_u),
  }
}
