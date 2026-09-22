import api from '../api/client'
import { VedProfile } from '../types/ved'

export async function createCompanyFromVed(profile: VedProfile): Promise<string | null> {
  try {
    const { data } = await api.post('/ved/create-and-link', {
      inn: profile.inn,
      name: profile.company_name,
      region: profile.region,
      address: profile.address,
      phone: profile.contact_phone,
      email: profile.contact_email,
      website: profile.website,
      director: profile.director,
      ogrn: profile.ogrn,
      activity_main: profile.activity,
      revenue: profile.revenue != null ? Math.round(profile.revenue) : null,
      employees: profile.employees,
      source_orig: profile.source_files?.join(', '),
    })
    return data.company_id
  } catch (e: any) {
    const msg = e?.response?.data?.detail || 'Ошибка при создании компании'
    alert(msg)
    return null
  }
}
