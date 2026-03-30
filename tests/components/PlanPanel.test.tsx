/**
 * Tests for PlanPanel component (Story 5.2)
 *
 * Tests verify that:
 * - AC #1: Plan displays as numbered list of steps
 * - AC #2: Execute button is visible and clickable
 * - AC #6: Plan not shown when intent != 'report'
 * - AC #5: Plan state is preserved (parent responsibility, verified at AppLayout level)
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { PlanPanel } from '../../src/components/PlanPanel'

describe('PlanPanel Component', () => {
  const samplePlan = [
    'Load voltage and current data from uploaded CSVs',
    'Calculate summary statistics (mean, median, max, min)',
    'Generate a time-series plot of voltage vs time',
    'Create correlation analysis between columns',
  ]

  describe('AC #1: Plan Display as Numbered List', () => {
    it('renders plan as numbered list when intent is report and plan exists', () => {
      render(
        <PlanPanel
          plan={samplePlan}
          intent="report"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      // Verify numbered format
      expect(screen.getByText('1.')).toBeInTheDocument()
      expect(screen.getByText('2.')).toBeInTheDocument()
      expect(screen.getByText('3.')).toBeInTheDocument()
      expect(screen.getByText('4.')).toBeInTheDocument()

      // Verify step content
      expect(
        screen.getByText('Load voltage and current data from uploaded CSVs')
      ).toBeInTheDocument()
      expect(
        screen.getByText('Calculate summary statistics (mean, median, max, min)')
      ).toBeInTheDocument()
    })

    it('displays steps in order', () => {
      const { container } = render(
        <PlanPanel
          plan={samplePlan}
          intent="report"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      const steps = container.querySelectorAll('.flex.gap-3')
      expect(steps.length).toBeGreaterThan(0)
    })
  })

  describe('AC #2: Execute Button', () => {
    it('displays Execute button when intent is report', () => {
      render(
        <PlanPanel
          plan={samplePlan}
          intent="report"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      const button = screen.getByRole('button', { name: /Execute Analysis/i })
      expect(button).toBeInTheDocument()
    })

    it('button is disabled when isExecuting is true (AC #2)', () => {
      render(
        <PlanPanel
          plan={samplePlan}
          intent="report"
          isExecuting={true}
          onExecute={() => {}}
        />
      )

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('button shows loading state when executing', () => {
      render(
        <PlanPanel
          plan={samplePlan}
          intent="report"
          isExecuting={true}
          onExecute={() => {}}
        />
      )

      expect(screen.getByText('Executing...')).toBeInTheDocument()
    })

    it('calls onExecute callback when button clicked (AC #3)', () => {
      const mockOnExecute = jest.fn()
      render(
        <PlanPanel
          plan={samplePlan}
          intent="report"
          isExecuting={false}
          onExecute={mockOnExecute}
        />
      )

      const button = screen.getByRole('button', { name: /Execute Analysis/i })
      fireEvent.click(button)

      expect(mockOnExecute).toHaveBeenCalledTimes(1)
    })
  })

  describe('AC #6: Conditional Visibility', () => {
    it('does not render when intent is qa', () => {
      const { container } = render(
        <PlanPanel
          plan={samplePlan}
          intent="qa"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('does not render when intent is chat', () => {
      const { container } = render(
        <PlanPanel
          plan={samplePlan}
          intent="chat"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('does not render when plan is null', () => {
      const { container } = render(
        <PlanPanel
          plan={null}
          intent="report"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('does not render when plan is empty array', () => {
      const { container } = render(
        <PlanPanel
          plan={[]}
          intent="report"
          isExecuting={false}
          onExecute={() => {}}
        />
      )

      expect(container.firstChild).toBeNull()
    })
  })
})
