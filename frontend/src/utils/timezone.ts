const REGION_TZ: Record<string, number> = {
  'Калининград': 2,
  'Москва': 3,
  'Московская': 3,
  'Санкт-Петербург': 3,
  'Ленинградская': 3,
  'Самара': 4,
  'Саратов': 4,
  'Ульяновск': 4,
  'Астрахань': 4,
  'Волгоград': 4,
  'Удмуртия': 4,
  'Екатеринбург': 5,
  'Свердловская': 5,
  'Тюмень': 5,
  'Ханты-Мансийск': 5,
  'Челябинск': 5,
  'Курган': 5,
  'Оренбург': 5,
  'Башкортостан': 5,
  'Пермь': 5,
  'Омск': 6,
  'Новосибирск': 7,
  'Томск': 7,
  'Кемерово': 7,
  'Красноярск': 7,
  'Алтай': 7,
  'Иркутск': 8,
  'Бурятия': 8,
  'Якутск': 9,
  'Забайкалье': 9,
  'Амурская': 9,
  'Владивосток': 10,
  'Приморье': 10,
  'Хабаровск': 10,
  'Сахалин': 11,
  'Магадан': 11,
  'Камчатка': 12,
  'Чукотка': 12,
}

export function getRegionUtcOffset(region: string | null | undefined): number {
  if (!region) return 3
  const lower = region.toLowerCase()
  for (const [key, offset] of Object.entries(REGION_TZ)) {
    if (lower.includes(key.toLowerCase())) return offset
  }
  return 3
}

export function getClientTimeInfo(region: string | null | undefined): { utcOffset: number; currentTime: string; period: 'working' | 'border' | 'off' } {
  const offset = getRegionUtcOffset(region)
  const now = new Date()
  const utcHours = now.getUTCHours()
  const utcMinutes = now.getUTCMinutes()
  const localHours = (utcHours + offset) % 24
  const localMinutes = utcMinutes
  const timeStr = `${String(localHours).padStart(2, '0')}:${String(localMinutes).padStart(2, '0')}`

  let period: 'working' | 'border' | 'off'
  if (localHours >= 9 && localHours < 18) {
    period = 'working'
  } else if ((localHours >= 8 && localHours < 9) || (localHours >= 18 && localHours < 20)) {
    period = 'border'
  } else {
    period = 'off'
  }

  return { utcOffset: offset, currentTime: timeStr, period }
}
