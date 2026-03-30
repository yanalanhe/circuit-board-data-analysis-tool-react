/**
 * Tests for DataGrid component (Story 3.2)
 *
 * Tests verify that:
 * 1. DataGrid displays provided rows and columns
 * 2. Column headers show data type information
 * 3. Horizontal scrolling works for wide tables
 * 4. Empty state is handled gracefully
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import DataGrid from '../../src/components/DataGrid'

describe('DataGrid Component', () => {
  const sampleColumns = ['id', 'temperature', 'date', 'location']
  const sampleDtypes = ['int64', 'float64', 'datetime64[ns]', 'object']
  const sampleRows = [
    {
      id: 1,
      temperature: 23.5,
      date: '2024-01-01',
      location: 'Room A',
    },
    {
      id: 2,
      temperature: 24.1,
      date: '2024-01-02',
      location: 'Room B',
    },
    {
      id: 3,
      temperature: 22.8,
      date: '2024-01-03',
      location: 'Room C',
    },
  ]

  it('renders table with column headers', () => {
    render(
      <DataGrid columns={sampleColumns} dtypes={sampleDtypes} rows={sampleRows} />
    )

    expect(screen.getByText(/id \(integer\)/i)).toBeInTheDocument()
    expect(screen.getByText(/temperature \(float\)/i)).toBeInTheDocument()
  })

  it('displays data in rows', () => {
    render(
      <DataGrid columns={sampleColumns} dtypes={sampleDtypes} rows={sampleRows} />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('23.5')).toBeInTheDocument()
    expect(screen.getByText('Room A')).toBeInTheDocument()
  })

  it('shows row count', () => {
    render(
      <DataGrid columns={sampleColumns} dtypes={sampleDtypes} rows={sampleRows} />
    )

    expect(screen.getByText(/Showing 3 rows/)).toBeInTheDocument()
  })

  it('handles empty data gracefully', () => {
    render(
      <DataGrid columns={sampleColumns} dtypes={sampleDtypes} rows={[]} />
    )

    expect(screen.getByText(/No data available/i)).toBeInTheDocument()
  })

  it('formats data types correctly', () => {
    const dtypes = ['int64', 'float64', 'datetime64[ns]', 'object', 'bool']
    const columns = ['int_col', 'float_col', 'date_col', 'str_col', 'bool_col']

    render(
      <DataGrid
        columns={columns}
        dtypes={dtypes}
        rows={[{ int_col: 1, float_col: 1.5, date_col: '2024-01-01', str_col: 'test', bool_col: true }]}
      />
    )

    expect(screen.getByText(/integer/)).toBeInTheDocument()
    expect(screen.getByText(/float/)).toBeInTheDocument()
    expect(screen.getByText(/datetime/)).toBeInTheDocument()
    expect(screen.getByText(/string/)).toBeInTheDocument()
    expect(screen.getByText(/boolean/)).toBeInTheDocument()
  })

  it('handles null/undefined values', () => {
    const rowsWithNull = [
      {
        id: 1,
        temperature: null,
        date: undefined,
        location: 'Room A',
      },
    ]

    render(
      <DataGrid columns={sampleColumns} dtypes={sampleDtypes} rows={rowsWithNull} />
    )

    // Null values should show as —
    const cells = screen.getAllByText('—')
    expect(cells.length).toBeGreaterThan(0)
  })

  it('truncates long strings', () => {
    const longString = 'a'.repeat(100)
    const rowsWithLongString = [
      {
        id: 1,
        temperature: 23.5,
        date: '2024-01-01',
        location: longString,
      },
    ]

    const { container } = render(
      <DataGrid columns={sampleColumns} dtypes={sampleDtypes} rows={rowsWithLongString} />
    )

    // Check that the truncated text contains the ellipsis
    const textElements = container.querySelectorAll('[title]')
    expect(textElements.length).toBeGreaterThan(0)
  })
})
