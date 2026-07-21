import { copyFile, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const webDir = resolve(scriptDir, '..')
const sourcePath = resolve(webDir, 'tests/fixtures/smoke-transactions.json')
const targetPath = resolve(webDir, '../parser/data/transactions.json')

await mkdir(dirname(targetPath), { recursive: true })
await copyFile(sourcePath, targetPath)
console.log(`Prepared synthetic smoke data at ${targetPath}`)
