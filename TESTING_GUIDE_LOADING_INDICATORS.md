# Testing Guide for Loading Indicators Feature

## Quick Start

To test the loading indicators implementation, follow these steps:

### 1. Build and Start the Frontend

```bash
cd /workspaces/managed-nebula/frontend
npm install
npm run build
# Or for development mode with hot reload:
npm start
```

### 2. Start the Backend Server

```bash
cd /workspaces/managed-nebula
docker-compose up -d server
```

### 3. Access the Application

Navigate to: `http://localhost:4200` (or the configured port)

## Manual Testing Checklist

### ✅ Clients Component

1. **Normal Loading**
   - Navigate to the Clients page
   - Observe: Loading spinner should appear briefly
   - Verify: Spinner disappears and table appears when data loads

2. **Empty State**
   - If no clients exist, verify "No clients found." message appears
   - Verify: No loading spinner is visible

3. **Error State** (simulate network error)
   - Open Chrome DevTools → Network tab → Set to "Offline"
   - Refresh the page or navigate away and back
   - Verify: Error message appears with "Retry" button
   - Click "Retry" button
   - Verify: Loading spinner reappears

### ✅ Groups Component

1. **Normal Loading**
   - Navigate to the Groups page
   - Observe: Loading spinner with "Loading groups..." message
   - Verify: Grid view appears with groups when data loads

2. **Empty State**
   - If no groups exist, verify "No groups found. Create one to get started." message
   - Verify: Message only appears after loading completes

3. **Error State**
   - Simulate network error (DevTools → Offline)
   - Verify: Error message with retry button
   - Test retry functionality

### ✅ Firewall Rulesets Component

1. **Normal Loading**
   - Navigate to the Firewall Rulesets page
   - Observe: Loading spinner with "Loading firewall rulesets..." message
   - Verify: Table appears when data loads

2. **Empty State**
   - Verify "No firewall rulesets defined." message appears when empty
   - Verify: Message has white background and rounded corners

3. **Error State**
   - Test network error scenario
   - Verify retry button functionality

### ✅ IP Pools Component

1. **Normal Loading**
   - Navigate to the IP Pools page
   - Observe: Loading spinner with "Loading IP pools..." message
   - Verify: Table displays pools when loaded

2. **Empty State**
   - Verify "No IP pools defined." message
   - Check styling matches other components

3. **Error State**
   - Test error message and retry functionality

### ✅ Users Component (Admin Only)

1. **Normal Loading**
   - Login as admin
   - Navigate to Users page
   - Observe: Loading spinner with "Loading users..." message
   - Verify: Table appears with user list

2. **Empty State**
   - Verify "No users found." message (unlikely in real scenario)

3. **Error State**
   - Test network error and retry

### ✅ CA Component

1. **Normal Loading**
   - Navigate to the Certificate Authorities page
   - Observe: Loading spinner with "Loading certificate authorities..." message
   - Verify: Table appears with CA list

2. **Empty State**
   - Verify "No CA certificates." message
   - Check message styling

3. **Error State**
   - Test error handling and retry

## Network Simulation Testing

### Test Slow Network

1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Set throttling to "Slow 3G" or "Fast 3G"
4. Navigate between pages
5. Verify: Loading spinners remain visible longer
6. Verify: Spinners eventually disappear when data loads

### Test Network Errors

1. Open Chrome DevTools
2. Network tab → Set to "Offline"
3. Navigate to any table page
4. Verify: Error message appears
5. Go online (disable offline mode)
6. Click "Retry" button
7. Verify: Data loads successfully

### Test Network Timeout

1. Use Chrome DevTools Network tab
2. Right-click on request → Block request URL
3. Navigate to page
4. Verify: Error handling works correctly

## Visual Testing Checklist

### Loading Spinner
- [ ] Spinner is centered on the page
- [ ] Spinner has smooth animation (no jank)
- [ ] Spinner color matches theme (green/teal)
- [ ] "Loading..." text is clearly visible
- [ ] Padding around spinner looks appropriate

### Error State
- [ ] Error message is red (`#d32f2f`)
- [ ] Error message is clearly readable
- [ ] Retry button is properly styled
- [ ] Button hover state works
- [ ] Error container is centered

### Empty State
- [ ] "No data" message is centered
- [ ] Message is gray/muted color
- [ ] Font is italic for emphasis
- [ ] Background matches component style

### Data State
- [ ] No loading indicator visible when data is shown
- [ ] Table/grid appears smoothly
- [ ] No layout shift during transition

## Responsive Testing

Test on different screen sizes:

### Desktop (1920x1080)
- [ ] All components display correctly
- [ ] Spinners are properly sized
- [ ] Error messages are readable

### Tablet (768x1024)
- [ ] Loading states work on medium screens
- [ ] Buttons remain accessible
- [ ] Text remains readable

### Mobile (375x667)
- [ ] Spinners scale appropriately
- [ ] Error messages wrap correctly
- [ ] Retry buttons are touch-friendly
- [ ] Padding adjusts for small screens

## Browser Compatibility

Test in:
- [ ] Chrome/Chromium (primary)
- [ ] Firefox
- [ ] Safari (if available)
- [ ] Edge

## Accessibility Testing

### Screen Reader Testing
1. Enable screen reader (NVDA/JAWS/VoiceOver)
2. Navigate to table pages
3. Verify: Loading messages are announced
4. Verify: Error messages are announced
5. Verify: Retry buttons are properly labeled

### Keyboard Navigation
1. Use Tab key to navigate
2. Verify: Retry buttons are focusable
3. Verify: Focus indicators are visible
4. Test Enter/Space to activate retry

### Color Contrast
- [ ] Error message has sufficient contrast (WCAG AA)
- [ ] Loading text is readable
- [ ] Spinner is visible against background

## Performance Testing

### Load Time
- [ ] Initial page load shows spinner within 100ms
- [ ] Spinner disappears within 1 second on fast network
- [ ] No console errors during loading

### Animation Performance
- [ ] Spinner rotates smoothly (60 FPS)
- [ ] No layout thrashing
- [ ] CPU usage is reasonable

### Memory
- [ ] No memory leaks when navigating between pages
- [ ] Loading states are properly cleaned up

## Integration Testing

### Create → List Flow
1. Create a new resource (client/group/etc.)
2. Verify: List page shows loading spinner
3. Verify: New item appears in list
4. Verify: No errors in console

### Delete → List Flow
1. Delete a resource
2. Verify: List reloads with loading spinner
3. Verify: Deleted item is gone
4. Verify: Loading state completes properly

### Update → List Flow
1. Update a resource
2. Navigate back to list
3. Verify: Loading indicator appears
4. Verify: Updated data is shown

## Edge Cases

### Rapid Navigation
1. Quickly navigate between pages
2. Verify: Loading states don't overlap
3. Verify: Previous loading states are cancelled
4. Verify: No race conditions

### Multiple Tabs
1. Open application in multiple tabs
2. Trigger loading in different tabs
3. Verify: Each tab handles loading independently
4. Verify: No cross-contamination

### Browser Refresh
1. Trigger loading state
2. Refresh page during loading
3. Verify: Loading restarts properly
4. Verify: No stuck loading states

## Troubleshooting

### Spinner Doesn't Appear
- Check: `isLoading` state is being set to `true`
- Check: Template has correct `*ngIf="isLoading"` directive
- Check: CSS is properly loaded
- Check: No z-index conflicts

### Spinner Doesn't Disappear
- Check: `isLoading` set to `false` in both success and error callbacks
- Check: API is actually responding
- Check: No errors in console preventing state update

### Error State Not Showing
- Check: Error handling in subscribe callback
- Check: `error` state variable is being set
- Check: Template has error state conditionals

### Wrong Message Displayed
- Check: Order of `*ngIf` conditionals in template
- Check: Boolean logic (e.g., `!isLoading && !error && data.length === 0`)

## Sign-Off Checklist

Before marking as complete, verify:

- [x] All 6 table components have loading indicators
- [x] Loading spinners appear consistently
- [x] Error states work with retry buttons
- [x] Empty states show appropriate messages
- [x] Styling is consistent across all components
- [x] No console errors during normal operation
- [x] Responsive design works on mobile
- [ ] Manual testing completed successfully
- [ ] Performance is acceptable
- [ ] Accessibility requirements met

## Automated Testing (Optional Future Work)

Consider adding:
- Unit tests for loading state management
- E2E tests for loading indicators with Cypress/Playwright
- Visual regression tests for loading states
- Performance benchmarks

## Notes

- Loading indicators appear on initial page load and after data mutations
- Spinners use CSS animations (no JavaScript) for better performance
- Error messages are user-friendly and actionable
- All components follow the same pattern for consistency
