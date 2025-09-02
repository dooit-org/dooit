import DefaultTheme from 'vitepress/theme'
import { useTUI } from 'vitepress-theme-tui'
import 'vitepress-theme-tui/style.css'

export default {
  extends: DefaultTheme,
  enhanceApp(ctx: any) {
    useTUI({
      theme: 'default',
    })
  },
}
