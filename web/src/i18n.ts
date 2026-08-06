import type { Lang, Localized } from './types'

export const STRINGS = {
  en: {
    justMet: 'You just met',
    saveContact: 'Save contact',
    saved: 'Contact card downloaded',
    whatsapp: 'WhatsApp',
    linkedin: 'LinkedIn',
    email: 'Email',
    call: 'Call',
    regulatory: 'Regulatory details',
    licensedBy: 'Licensed corporation',
    entityCe: 'Entity CE No.',
    ceNumber: 'SFC CE No.',
    askNexus: 'Ask Nexus',
    chatOffline:
      'The assistant is not switched on for this deployment yet — the contact details above all work.',
    placeholder: 'Ask about Nexus…',
    send: 'Send',
    stop: 'Stop',
    thinking: 'Thinking',
    sources: 'Sources',
    retry: 'Try again',
    errorNetwork: "Couldn't reach the assistant. Check your connection and try again.",
    errorRate: 'That was a lot of questions at once — give it a few seconds.',
    errorGeneric: 'Something went wrong on our side. Try again in a moment.',
    cardNotFound: 'This card link is not recognised.',
    cardNotFoundBody: 'Double-check the QR code, or reach us at hello@noahnexus.ai.',
    loading: 'Loading',
    website: 'noahnexus.ai',
    disclaimer:
      'For information only. Not investment advice, a recommendation, or an offer to buy or sell any product. The assistant answers from a public knowledge base and can be wrong; nothing it says is binding. Regulated services are provided by licensed entities in their respective jurisdictions.',
    poweredBy: 'Nexus AI · knowledge-base assistant',
  },
  zh: {
    justMet: '你刚认识',
    saveContact: '保存联系人',
    saved: '联系人已下载',
    whatsapp: 'WhatsApp',
    linkedin: 'LinkedIn',
    email: '邮箱',
    call: '电话',
    regulatory: '监管信息',
    licensedBy: '持牌法团',
    entityCe: '中央编号',
    ceNumber: 'SFC 中央编号',
    askNexus: '问 Nexus',
    chatOffline: '这个部署还没接上助手 —— 上面的联系方式都是可用的。',
    placeholder: '想了解 Nexus 什么？',
    send: '发送',
    stop: '停止',
    thinking: '思考中',
    sources: '资料来源',
    retry: '重试',
    errorNetwork: '连不上助手，检查一下网络再试。',
    errorRate: '问得有点快，等几秒再来。',
    errorGeneric: '我们这边出了点问题，稍后再试。',
    cardNotFound: '这个名片链接无法识别。',
    cardNotFoundBody: '请核对二维码，或联系 hello@noahnexus.ai。',
    loading: '加载中',
    website: 'noahnexus.ai',
    disclaimer:
      '本页信息仅供参考，不构成投资建议、推荐或任何产品的要约。助手基于公开知识库作答，可能出错，其内容不具约束力。受规管服务由各司法辖区的持牌实体提供。',
    poweredBy: 'Nexus AI · 知识库助手',
  },
} as const satisfies Record<Lang, Record<string, string>>

export type StringKey = keyof (typeof STRINGS)['en']

export function t(lang: Lang, key: StringKey): string {
  return STRINGS[lang][key]
}

export function pick(value: Localized | undefined | null, lang: Lang): string {
  if (!value) return ''
  return lang === 'zh' ? value.zh : value.en
}

/** The other language's rendering, when both are worth showing side by side. */
export function other(value: Localized | undefined | null, lang: Lang): string {
  if (!value) return ''
  const primary = pick(value, lang)
  const secondary = lang === 'zh' ? value.en : value.zh
  return secondary && secondary !== primary ? secondary : ''
}

export function detectLang(): Lang {
  const fromQuery = new URLSearchParams(window.location.search).get('lang')
  if (fromQuery === 'zh' || fromQuery === 'en') return fromQuery

  const stored = localStorage.getItem('nexus-card-lang')
  if (stored === 'zh' || stored === 'en') return stored

  const preferred = navigator.languages ?? [navigator.language]
  return preferred.some((code) => code.toLowerCase().startsWith('zh')) ? 'zh' : 'en'
}
