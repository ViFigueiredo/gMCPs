import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'

import './main.css'
import App from './App.vue'
import router from './router/index.ts'
import ptBR from './locales/pt-BR.json'
import enUS from './locales/en-US.json'

const saved = localStorage.getItem('locale')
const browserLang = navigator.language || 'pt-BR'
const locale = saved || (browserLang.startsWith('en') ? 'en-US' : 'pt-BR')

const i18n = createI18n({
  locale,
  fallbackLocale: 'pt-BR',
  messages: { 'pt-BR': ptBR, 'en-US': enUS },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')
