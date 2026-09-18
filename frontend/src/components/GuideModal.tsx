import { useState } from 'react'

const GUIDE_KEY = 'novel_crm_guide_seen_v2'

const steps = [
  {
    id: 'start',
    title: 'Привет! 👋',
    text: `Это короткий мануал по Novel CRM. Покажу главные вкладки и как в них работать. Один раз посмотрите — и он больше не будет показываться. Чтобы открыть его снова — нажмите «?» в правом верхнем углу.`,
  },
  {
    id: 'companies',
    title: '1. Вкладка «Компании»',
    text: `Здесь весь список компаний. Нажмите на любую строку — справа откроется карточка компании. В карточке 4 вкладки: Активность, Коммуникации, Данные, AI.`,
  },
  {
    id: 'activity',
    title: '2. «Активность» — звонки и статусы',
    text: `Вверху выберите статус (Новый, Заинтересован, Думают, Отказ...), напишите результат звонка и нажмите «Сохранить звонок». Строка появится в истории звонков ниже.`,
  },
  {
    id: 'meeting',
    title: '3. Как назначить встречу',
    text: `Откройте карточку компании → блок «Встреча». Нажмите «Назначить (быстро)», выберите дату и время, добавьте заметки (место, тема) и сохраните. Встреча появится в календаре, а вам и руководителю придёт уведомление в Telegram.`,
  },
  {
    id: 'meeting-date',
    title: '4. Встреча назначена, но нет даты ⚠',
    text: `В воронке у компаний со статусом «Встреча назначена» появляется пометка «⚠ нет даты». Это значит: договорились о встрече, но время ещё не проставлено. Откройте карточку → блок «Встреча» → выберите дату/время → сохраните. После этого напоминания (за сутки, час и 10 минут) будут приходить вам и руководителю в Telegram.`,
  },
  {
    id: 'pipeline',
    title: '5. Вкладка «Воронка»',
    text: `Здесь компании разложены по этапам: Новый → Сообщение отправлено → Диагностика пройдена → Тест предложен → Тест выполнен → Резерв → Клиент → Партнёр.`,
  },
  {
    id: 'pipeline-move',
    title: '6. Как двигать по воронке',
    text: `На карточке компании в воронке нажмите стрелку «→» и выберите следующий этап. Например, после успешного разговора — «Диагностика пройдена». Статус звонка при этом ставится отдельно во вкладке «Активность».`,
  },
  {
    id: 'ved',
    title: '7. Вкладка «ВЭД» — таможенные декларации',
    text: `Здесь загружены данные по 4 Excel-файлам ВЭД (импорт/экспорт). Всего 8000+ профилей компаний с ИНН, товарами, странами, таможенной стоимостью.\n\n• Таблица с поиском, фильтрами по странам/кодам ТН ВЭД и пагинацией.\n• Клик по строке → панель справа с декларациями, контактами, сайтом.\n• Если компания уже есть в CRM — кнопка «Открыть в CRM» переключит вас на её карточку.\n• Если нет — кнопка «+ Создать в CRM» создаст компанию с заполненными данными (ИНН, название, директор, адрес, телефон, email, сайт, ОГРН, деятельность, выручка, сотрудники) и откроет карточку.\n• Из карточки компании в CRM — кнопка «📊 ВЭД» в шапке открывает профиль этой компании во вкладке ВЭД.`,
  },
  {
    id: 'reminders',
    title: '8. Вкладка «Напоминания» — отложенные письма',
    text: `Раньше это называлось «Follow-up». Здесь список всех запланированных писем по всем компаниям.\n\n• Статистика сверху: всего, ожидают отправки, просрочено, отправлено, отменено.\n• Поиск по теме, email, названию компании.\n• Фильтр по статусу: Ожидает / Отправлено / Отменено / Ошибка.\n• Просроченные подсвечиваются красным.\n• Действия: для ожидающих — «Отменить», для отменённых — «Активировать».\n\nСоздание: в карточке компании → вкладка «Коммуникации» → «Создать напоминание». Укажите email, тему, текст, дату/время отправки. Письмо уйдёт автоматически.`,
  },
  {
    id: 'comms',
    title: '9. Вкладка «Коммуникации»',
    text: `Здесь вся работа с письмами:\n• 📄 КП — скачать или отправить коммерческое предложение клиенту;\n• ✉️ Написать письмо — отправить email вручную;\n• ⏰ Создать напоминание — запланировать повторное письмо (попадёт во вкладку «Напоминания»);\n• Email-история — все отправленные письма и их статус (открыто/не открыто).`,
  },
  {
    id: 'ai',
    title: '10. Вкладка «AI»',
    text: `Здесь ИИ помогает с компанией: генерирует саммари, подсказывает аргументы для разговора и подставляет данные в карточку. Пользуйтесь перед звонком — быстрее подготовитесь.`,
  },
  {
    id: 'dashboard',
    title: '11. Сводка наверху',
    text: `Вверху — счётчики: задачи на сегодня, просроченные, звонки, компании в воронке. Клик по этапу воронке отфильтрует список компаний по этому этапу.`,
  },
  {
    id: 'end',
    title: 'Всё! 🎉',
    text: `Помните главное:\n• После звонка — сохраняйте статус и результат.\n• Договорились о встрече — сразу проставьте дату и время в блоке «Встреча».\n• Напоминания — для повторных писем через несколько дней (вкладка «Напоминания»).\n• ВЭД — для поиска компаний по таможенным данным и быстрого создания в CRM.\n\nУдачи в работе!`,
  },
]

export default function GuideModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [idx, setIdx] = useState(0)
  const step = steps[idx]
  const isLast = idx === steps.length - 1

  const finish = () => {
    try { localStorage.setItem(GUIDE_KEY, '1') } catch {}
    onClose()
    setIdx(0)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" onClick={onClose}>
      <div className="bg-surface rounded-xl w-[480px] max-w-[92vw] shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="h-1 bg-accent" style={{ width: `${((idx + 1) / steps.length) * 100}%`, transition: 'width 0.3s' }} />
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <div className="flex items-start justify-between mb-3">
            <h2 className="text-lg font-bold">{step.title}</h2>
            <button onClick={onClose} className="text-muted hover:text-text text-lg leading-none">✕</button>
          </div>
          <p className="text-sm text-text/90 whitespace-pre-wrap leading-relaxed">{step.text}</p>
        </div>
        <div className="flex items-center justify-between px-6 py-4 border-t border-muted/10">
          <button
            onClick={() => setIdx(i => Math.max(0, i - 1))}
            disabled={idx === 0}
            className="px-3 py-1.5 text-sm text-muted hover:text-text disabled:opacity-30 transition-colors"
          >
            ← Назад
          </button>
          <div className="flex gap-1.5">
            {steps.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setIdx(i)}
                className={`w-2 h-2 rounded-full transition-colors ${i === idx ? 'bg-accent w-4' : 'bg-muted/30 hover:bg-muted/50'}`}
                aria-label={`Шаг ${i + 1}`}
              />
            ))}
          </div>
          {isLast ? (
            <button
              onClick={finish}
              className="px-4 py-1.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Готово
            </button>
          ) : (
            <button
              onClick={() => setIdx(i => Math.min(steps.length - 1, i + 1))}
              className="px-4 py-1.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Далее →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function shouldShowGuide(): boolean {
  try {
    return localStorage.getItem(GUIDE_KEY) !== '1'
  } catch {
    return false
  }
}
