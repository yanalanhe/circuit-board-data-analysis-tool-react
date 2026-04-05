'use client'

import React, { useMemo, useState, useCallback, useRef, useEffect } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  ColumnDef,
  HeaderGroup,
  Row,
  Cell,
  CellContext,
} from '@tanstack/react-table'

interface EditState {
  rowIndex: number
  columnKey: string
  originalValue: unknown
  editValue: string
  error: string | null
}

interface DataGridProps {
  columns: string[]
  dtypes: string[]
  rows: Record<string, unknown>[]
  onCellSave?: (rowIndex: number, column: string, value: unknown) => Promise<void>
}

/**
 * DataGrid component displays CSV data in a table format with cell editing support
 * Uses tanstack-table for performance and flexibility
 *
 * Features:
 * - Column headers with data type information
 * - Cell editing with type validation
 * - Keyboard shortcuts: Enter (save), Escape (cancel), Tab (next)
 * - Mouse interactions: click to edit, blur to save
 * - Horizontal scrolling for wide datasets
 * - Clean, professional styling with Tailwind
 */
export default function DataGrid({ columns, dtypes, rows, onCellSave }: DataGridProps) {
  const [editState, setEditState] = useState<EditState | null>(null)
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(null)
  const [isSaving, setIsSaving] = useState(false)

  // Focus input when entering edit mode
  useEffect(() => {
    if (editState && inputRef.current) {
      inputRef.current.focus()
      if (inputRef.current instanceof HTMLInputElement) {
        inputRef.current.select()
      }
    }
  }, [editState])

  // Build column definitions from column names and types
  const columnDefs = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
    return columns.map((col, idx) => ({
      header: `${col} (${formatDataType(dtypes[idx])})`,
      accessorKey: col,
      cell: (info: CellContext<Record<string, unknown>, unknown>) => {
        const value = info.getValue()
        const rowIndex = info.row.index
        const isEditing = editState?.rowIndex === rowIndex && editState?.columnKey === col

        if (isEditing && editState) {
          return (
            <EditableCell
              dtype={dtypes[idx]}
              value={editState.editValue}
              error={editState.error}
              onChange={(newValue) => {
                setEditState({ ...editState, editValue: newValue, error: null })
              }}
              onSave={() => handleSaveCell(rowIndex, col, editState.editValue, dtypes[idx])}
              onCancel={handleCancelEdit}
              inputRef={inputRef}
              isSaving={isSaving}
            />
          )
        }

        return (
          <div
            onClick={() => handleEditCell(rowIndex, col, value)}
            className="cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/30 px-1 py-1 rounded transition-colors"
            title="Click to edit"
          >
            {formatCellValue(value)}
          </div>
        )
      },
    }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columns, dtypes, editState, isSaving])

  const handleEditCell = useCallback((rowIndex: number, columnKey: string, originalValue: unknown) => {
    setEditState({
      rowIndex,
      columnKey,
      originalValue,
      editValue: originalValue !== null && originalValue !== undefined ? String(originalValue) : '',
      error: null,
    })
  }, [])

  const handleCancelEdit = useCallback(() => {
    setEditState(null)
  }, [])

  const handleSaveCell = useCallback(
    async (rowIndex: number, columnKey: string, editValue: string, dtype: string) => {
      // Validate input
      const validationError = validateInput(editValue, dtype)
      if (validationError) {
        setEditState((prev) => prev ? { ...prev, error: validationError } : null)
        return
      }

      // Convert value based on dtype
      const convertedValue = convertValue(editValue, dtype)

      setIsSaving(true)
      try {
        if (onCellSave) {
          await onCellSave(rowIndex, columnKey, convertedValue)
        }
        setEditState(null)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to save cell'
        setEditState((prev) => prev ? { ...prev, error: errorMessage } : null)
      } finally {
        setIsSaving(false)
      }
    },
    [onCellSave]
  )

  // Create table instance
  const table = useReactTable({
    data: rows,
    columns: columnDefs,
    getCoreRowModel: getCoreRowModel(),
  })

  // Handle empty data
  if (rows.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No data available
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Table container with scroll */}
      <div className="flex-1 overflow-auto border border-gray-200 dark:border-gray-700 rounded">
        <table className="w-full border-collapse text-sm">
          {/* Header */}
          <thead className="sticky top-0 bg-gray-50 dark:bg-gray-800">
            {table.getHeaderGroups().map((headerGroup: HeaderGroup<Record<string, unknown>>) => (
              <tr key={headerGroup.id} className="border-b border-gray-200 dark:border-gray-700">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap bg-gray-50 dark:bg-gray-800"
                    title={header.getContext().header.column.columnDef.header?.toString()}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          {/* Body */}
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {table.getRowModel().rows.map((row: Row<Record<string, unknown>>) => (
              <tr key={row.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                {row.getVisibleCells().map((cell: Cell<Record<string, unknown>, unknown>) => (
                  <td
                    key={cell.id}
                    className="px-3 py-2 text-gray-900 dark:text-gray-100 whitespace-nowrap overflow-hidden text-ellipsis"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Row count */}
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
        Showing {rows.length} rows
      </div>
    </div>
  )
}

/**
 * EditableCell component for in-place cell editing
 */
interface EditableCellProps {
  dtype: string
  value: string
  error: string | null
  onChange: (value: string) => void
  onSave: () => Promise<void>
  onCancel: () => void
  inputRef: React.RefObject<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  isSaving: boolean
}

function EditableCell({
  dtype,
  value,
  error,
  onChange,
  onSave,
  onCancel,
  inputRef,
  isSaving,
}: EditableCellProps) {
  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      await onSave()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onCancel()
    } else if (e.key === 'Tab') {
      e.preventDefault()
      await onSave()
    }
  }

  const handleBlur = async () => {
    // Save on blur (click outside)
    if (!isSaving) {
      await onSave()
    }
  }

  const inputType = getInputType(dtype)

  return (
    <div className={`${error ? 'border-2 border-red-500 rounded' : ''}`}>
      {inputType === 'select' ? (
        <select
          ref={inputRef as React.RefObject<HTMLSelectElement>}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          disabled={isSaving}
          className={`w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            error ? 'border-red-500' : 'border-blue-400'
          } ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      ) : (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type={inputType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          disabled={isSaving}
          step={inputType === 'number' && dtype.includes('float') ? '0.01' : undefined}
          className={`w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            error ? 'border-red-500' : 'border-blue-400'
          } ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
        />
      )}
      {error && <div className="text-red-500 text-xs mt-1">{error}</div>}
    </div>
  )
}

/**
 * Determine appropriate HTML input type based on pandas dtype
 */
function getInputType(dtype: string): string {
  if (dtype.includes('int')) return 'number'
  if (dtype.includes('float')) return 'number'
  if (dtype.includes('datetime')) return 'date'
  if (dtype.includes('bool')) return 'select'
  return 'text'
}

/**
 * Validate input value against expected data type
 */
function validateInput(value: string, dtype: string): string | null {
  // Empty string is invalid for most types (except object/string)
  if (value === '') {
    if (dtype.includes('object') || dtype.includes('string')) {
      return null
    }
    return 'Value cannot be empty'
  }

  if (dtype.includes('int')) {
    if (!/^-?\d+$/.test(value)) {
      return 'Invalid integer: must be a whole number'
    }
    const num = parseInt(value, 10)
    if (num < -9223372036854775808 || num > 9223372036854775807) {
      return 'Integer out of valid range'
    }
  } else if (dtype.includes('float')) {
    if (!/^-?\d+(\.\d+)?$/.test(value)) {
      return 'Invalid float: must be a number'
    }
  } else if (dtype.includes('bool')) {
    if (value !== 'true' && value !== 'false') {
      return 'Invalid boolean: must be true or false'
    }
  } else if (dtype.includes('datetime')) {
    // Basic date validation - can be expanded
    if (!/^\d{4}-\d{2}-\d{2}/.test(value)) {
      return 'Invalid date format: expected YYYY-MM-DD'
    }
  }

  return null
}

/**
 * Convert string value to appropriate type
 */
function convertValue(value: string, dtype: string): unknown {
  if (dtype.includes('int')) {
    return parseInt(value, 10)
  } else if (dtype.includes('float')) {
    return parseFloat(value)
  } else if (dtype.includes('bool')) {
    return value === 'true'
  } else if (dtype.includes('datetime')) {
    return new Date(value).toISOString()
  }
  return value
}

/**
 * Format data type string for display
 * Examples: int64 → integer, float64 → float, object → string
 */
function formatDataType(dtype: string): string {
  if (!dtype) return 'unknown'

  // Handle pandas dtype strings
  if (dtype.includes('int')) return 'integer'
  if (dtype.includes('float')) return 'float'
  if (dtype.includes('datetime')) return 'datetime'
  if (dtype.includes('bool')) return 'boolean'
  if (dtype.includes('object')) return 'string'
  if (dtype.includes('string')) return 'string'

  // Return as-is if unrecognized
  return dtype.replace('64', '').replace('32', '')
}

/**
 * Format cell values for display
 */
function formatCellValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-gray-400">—</span>
  }

  if (typeof value === 'boolean') {
    return <span className="text-gray-700">{value ? 'true' : 'false'}</span>
  }

  if (typeof value === 'number') {
    return <span className="text-gray-700">{value.toLocaleString()}</span>
  }

  if (typeof value === 'string') {
    // Truncate long strings
    const maxLength = 50
    if (value.length > maxLength) {
      return (
        <span title={value} className="text-gray-700">
          {value.substring(0, maxLength)}…
        </span>
      )
    }
    return <span className="text-gray-700">{value}</span>
  }

  // For objects, convert to string
  return <span className="text-gray-700">{JSON.stringify(value)}</span>
}
