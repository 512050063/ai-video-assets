/**
 * 会话存储统一出口
 * - localStorage  ：勾选「记住密码」时保存 token / 用户信息 / 账号密码，关掉浏览器也在
 * - sessionStorage：未勾选时保存 token / 用户信息，关闭浏览器即失效
 */
const TOKEN_KEY = 'avm_token'
const USER_KEY = 'avm_user'
export const CREDS_KEY = 'avm_creds'

export function safeGet(store, key) {
  try {
    return store.getItem(key)
  } catch (e) {
    return null
  }
}

export function safeSet(store, key, value) {
  try {
    store.setItem(key, value)
  } catch (e) {
    /* 忽略隐私模式下的写入异常 */
  }
}

export function safeRemove(store, key) {
  try {
    store.removeItem(key)
  } catch (e) {
    /* 忽略隐私模式下的写入异常 */
  }
}

/* token 可能在两个存储里，取到的即为当前生效会话 */
export function readToken() {
  return safeGet(localStorage, TOKEN_KEY) || safeGet(sessionStorage, TOKEN_KEY) || ''
}

export function readUser() {
  const raw = safeGet(localStorage, USER_KEY) || safeGet(sessionStorage, USER_KEY)
  try {
    return JSON.parse(raw || 'null')
  } catch (e) {
    return null
  }
}

/* 当前会话实际使用的存储（localStorage 优先） */
export function activeStore() {
  return safeGet(localStorage, TOKEN_KEY) ? localStorage : sessionStorage
}

/* 记住的账号密码（仅在勾选「记住密码」时写入） */
export function readCreds() {
  try {
    return JSON.parse(safeGet(localStorage, CREDS_KEY) || 'null')
  } catch (e) {
    return null
  }
}

export function writeCreds(creds) {
  if (creds) {
    safeSet(localStorage, CREDS_KEY, JSON.stringify(creds))
  } else {
    safeRemove(localStorage, CREDS_KEY)
  }
}

/* 清除登录态（两个存储都清） */
export function clearSession() {
  safeRemove(localStorage, TOKEN_KEY)
  safeRemove(localStorage, USER_KEY)
  safeRemove(sessionStorage, TOKEN_KEY)
  safeRemove(sessionStorage, USER_KEY)
}
