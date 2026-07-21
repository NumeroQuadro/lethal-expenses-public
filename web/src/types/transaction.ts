import { z } from 'zod'

export const bankSchema = z.enum(['sberbank', 'yandex', 'ozon', 'spb'])
export const currencySchema = z.literal('RUB')
export const precisionSchema = z.enum(['second', 'minute', 'date'])

export const transactionSchema = z.object({
  id: z.string(),
  date: z.string().refine((value) => !Number.isNaN(Date.parse(value)), {
    message: 'Transaction date must be a valid ISO datetime string',
  }),
  amount: z.string().regex(/^[+-]?\d+(?:\.\d+)?$/, {
    message: 'Transaction amount must be a decimal string',
  }),
  currency: currencySchema,
  merchant_raw: z.string(),
  description: z.string(),
  bank: bankSchema,
  account: z.union([z.literal('ЭДС'), z.string().regex(/^\*{4}\d{4}$/)]),
  precision: precisionSchema,
  category: z.string(),
  is_transfer: z.boolean(),
  is_external_account: z.boolean().default(false),
  transfer_pair_id: z.string().nullable(),
  raw: z.record(z.string(), z.unknown()),
})

export const transactionsSchema = z.array(transactionSchema)

export type BankName = z.infer<typeof bankSchema>
export type CurrencyCode = z.infer<typeof currencySchema>
export type TransactionPrecision = z.infer<typeof precisionSchema>
export type Transaction = z.infer<typeof transactionSchema>

export function parseTransactions(input: unknown): Transaction[] {
  return transactionsSchema.parse(input)
}
