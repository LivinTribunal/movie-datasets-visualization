/** Caches the last call; arguments are compared with Object.is. */
export function memoLast<A extends unknown[], R>(fn: (...args: A) => R): (...args: A) => R {
  let last: { args: A; result: R } | null = null
  return (...args: A) => {
    if (last && last.args.length === args.length && last.args.every((a, i) => Object.is(a, args[i]))) {
      return last.result
    }
    const result = fn(...args)
    last = { args, result }
    return result
  }
}
