import { copyFile, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const webDir = resolve(scriptDir, '..')
const sourcePath = resolve(webDir, '../parser/data/transactions.json')
const targetPath = resolve(webDir, 'src/data/transactions.json')

try {
  await mkdir(dirname(targetPath), { recursive: true })
  await copyFile(sourcePath, targetPath)
  console.log(`Synced parser data to ${targetPath}`)
} catch (error) {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`Failed to sync parser data from ${sourcePath}: ${message}`)
  process.exitCode = 1
}
