export function pluralRu(
  count: number,
  forms: [singular: string, paucal: string, plural: string],
): string {
  const absoluteCount = Math.abs(count)
  const mod10 = absoluteCount % 10
  const mod100 = absoluteCount % 100

  if (mod10 === 1 && mod100 !== 11) {
    return forms[0]
  }

  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) {
    return forms[1]
  }

  return forms[2]
}
