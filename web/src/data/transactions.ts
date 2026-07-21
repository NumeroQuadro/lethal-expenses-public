import rawTransactions from './transactions.json'

import { parseTransactions } from '../types/transaction'

export const transactions = parseTransactions(rawTransactions)
