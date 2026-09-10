import { Converter } from 'opencc-js/cn2t'
export const traditional = Converter({ from: 'cn', to: 'tw' })
export const traditionalMarkup = markup => markup.replace(/>([^<>]+)</g, (_, text) => `>${traditional(text)}<`)
