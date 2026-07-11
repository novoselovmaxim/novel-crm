const pipelineColors: Record<string, string> = {
  new: 'bg-gray-500/20 text-gray-400',
  message_sent: 'bg-blue-500/20 text-blue-400',
  diagnosis_done: 'bg-yellow-500/20 text-yellow-400',
  test_offered: 'bg-sky-500/20 text-sky-400',
  test_done: 'bg-green-500/20 text-green-400',
  reserve: 'bg-purple-500/20 text-purple-400',
  client: 'bg-emerald-500/20 text-emerald-400',
  partner: 'bg-amber-500/20 text-amber-400',
}

const pipelineLabels: Record<string, string> = {
  new: 'Новый',
  message_sent: 'Сообщение отправлено',
  diagnosis_done: 'Диагностика пройдена',
  test_offered: 'Тест предложен',
  test_done: 'Тест выполнен',
  reserve: 'Резерв',
  client: 'Клиент',
  partner: 'Партнёр',
}

const tgColors: Record<string, string> = {
  none: 'bg-gray-500/20 text-gray-400',
  contacted: 'bg-yellow-500/20 text-yellow-400',
  responded: 'bg-green-500/20 text-green-400',
  no_response: 'bg-red-500/20 text-red-400',
}

const tgLabels: Record<string, string> = {
  none: 'Нет TG',
  contacted: 'Связались',
  responded: 'Ответил',
  no_response: 'Не ответил',
}

export default function StatusBadge({ status, kind = 'call' }: { status: string; kind?: 'call' | 'pipeline' | 'tg' }) {
  let colors: Record<string, string> = {}
  let labels: Record<string, string> = {}

  if (kind === 'pipeline') {
    colors = pipelineColors
    labels = pipelineLabels
  } else if (kind === 'tg') {
    colors = tgColors
    labels = tgLabels
  } else {
    const callColors: Record<string, string> = {
      new: 'bg-gray-500/20 text-gray-400',
      not_reached: 'bg-orange-500/20 text-orange-400',
      no_answer: 'bg-red-500/20 text-red-400',
      callback: 'bg-blue-500/20 text-blue-400',
      in_progress: 'bg-yellow-500/20 text-yellow-400',
      interested: 'bg-green-500/20 text-green-400',
      thinking: 'bg-teal-500/20 text-teal-400',
      meeting: 'bg-purple-500/20 text-purple-400',
      refused: 'bg-gray-600/20 text-gray-500',
    }
    const callLabels: Record<string, string> = {
      new: 'Новый',
      not_reached: 'Не дозвонился',
      no_answer: 'Не отвечает',
      callback: 'Перезвонить',
      in_progress: 'В работе',
      interested: 'Заинтересован',
      thinking: 'Думают',
      meeting: 'Встреча назначена',
      refused: 'Отказ',
    }
    colors = callColors
    labels = callLabels
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors[status] || colors.new || ''}`}>
      {labels[status] || status}
    </span>
  )
}
