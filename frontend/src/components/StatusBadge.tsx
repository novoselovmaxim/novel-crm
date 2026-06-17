const statusColors: Record<string, string> = {
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

const statusLabels: Record<string, string> = {
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

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[status] || statusColors.new}`}>
      {statusLabels[status] || status}
    </span>
  )
}
