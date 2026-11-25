/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        // 映射到 Element Plus 主色 #409EFF 体系
        brand: {
          50: '#ecf5ff',
          100: '#d9ecff',
          200: '#c6e2ff',
          300: '#a0cfff',
          400: '#79bbff',
          500: '#409eff',
          600: '#337ecc',
          700: '#2a6eb3'
        },
        // 中性色重映射到 EP 灰阶
        slate: {
          50: '#fafafa',
          100: '#f5f7fa',
          200: '#ebeef5',
          300: '#e4e7ed',
          400: '#dcdfe6',
          500: '#909399',
          600: '#606266',
          700: '#4c4d4f',
          800: '#303133',
          900: '#303133'
        }
      },
      boxShadow: {
        low: '0 1px 3px rgba(0,0,0,0.05)',
        medium: '0 2px 8px rgba(0,0,0,0.04)',
        high: '0 4px 16px rgba(0,0,0,0.08)'
      },
      borderRadius: {
        sm: '4px',
        md: '8px',
        lg: '12px'
      }
    }
  },
  plugins: []
}
