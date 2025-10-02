# EventDayBuddy Google Sheets Integration Tests

## Sheets Integration Test Scenarios

These tests verify the Google Sheets integration works correctly for data import/export.

### 1. Sheet Structure Verification

**Test Case:** Verify required sheet tabs exist
1. Check Master sheet exists with correct columns
2. Check Event-specific sheets are created automatically
3. Verify column headers match expected format

**Expected Columns (Master Sheet):**
- ticket_ref, name, id_number, phone, male_dep, resort_dep
- paid_amount, transfer_ref, ticket_type, arrival_time, departure_time
- status, id_doc_url, group_id, created_at, updated_at
- ArrivalBoatBoarded, DepartureBoatBoarded, checkin_time

### 2. Booking Export to Sheets

**Test Case:** New booking appears in sheets
1. Create booking via Telegram: `/newbooking` TEST001
2. Wait 30 seconds for sync
3. Check Master sheet for new row
4. Check Event sheet for new row
5. Verify all data matches exactly

**Verification Query:**
```sql
SELECT * FROM bookings WHERE ticket_ref = 'TEST001';
```
Compare with Sheets data row.

### 3. Check-in Status Sync

**Test Case:** Check-in updates propagate to sheets
1. Check in passenger: `/i ID001`
2. Wait 30 seconds for sync
3. Verify in sheets:
   - status = "checked_in"
   - ArrivalBoatBoarded = "1"
   - checkin_time = current timestamp

### 4. Bulk Import from Sheets

**Test Case:** Import bookings from CSV
1. Prepare CSV with test data (see manual_test_cases.md)
2. Send `/newbookings Test Event 2024` command
3. Upload CSV file
4. Verify bot processes import
5. Check database for new bookings
6. Verify sheets updated with new data

**Sample CSV for Testing:**
```csv
ticket_ref,name,id_number,phone,male_dep,resort_dep,paid_amount,transfer_ref,ticket_type,arrival_time,departure_time
TEST004,Alice Cooper,ID004,+1234567893,Male Airport,Test Resort,125.00,TR002,Premium,2024-01-15 11:00:00,2024-01-20 15:00:00
TEST005,Bob Wilson,ID005,+1234567894,Male Airport,Test Resort,150.00,TR003,Standard,2024-01-15 12:00:00,2024-01-20 16:00:00
```

### 5. Real-time Sync Verification

**Test Case:** Changes sync in real-time
1. Edit booking via `/editbooking ID001`
2. Change passenger name to "Johnathan Doe"
3. Wait 30 seconds
4. Verify sheets updated with new name
5. Check booking_edit_logs for audit trail

### 6. PDF Export Tests

**Test Case:** Boat manifest PDF generation
1. Complete check-in workflow for Boat 1
2. Use bot interface to export PDF
3. Verify PDF contains:
   - Correct boat number and event
   - All checked-in passengers
   - Accurate passenger details
   - Proper formatting

**Test Case:** ID cards PDF generation
1. Use bot interface to export ID cards
2. Verify PDF contains:
   - Individual cards for each passenger
   - Photos if attached
   - Passenger details and boat assignments

### 7. Error Handling in Sheets

**Test Case:** Handle sheets API errors gracefully
1. Simulate sheets API outage
2. Create booking via bot
3. Verify bot handles error gracefully
4. Check error logs for proper logging
5. Verify system continues functioning

### 8. Data Consistency Tests

**Test Case:** Cross-system data integrity
1. Create booking in database directly
2. Verify it appears in sheets (or not, depending on sync direction)
3. Create booking via bot
4. Verify it appears in both systems
5. Compare data between database and sheets for accuracy

### 9. Performance Tests

**Test Case:** Large dataset handling
1. Import 50+ bookings via CSV
2. Monitor sync time to sheets
3. Verify all data transfers correctly
4. Check for any data loss or corruption

### 10. Backup and Recovery

**Test Case:** Data preservation during issues
1. Create test bookings
2. Verify in both database and sheets
3. Simulate system recovery
4. Verify data integrity maintained

## Sheets API Configuration Tests

### Authentication Verification
1. Verify Google Cloud credentials configured
2. Verify Sheets API enabled
3. Verify correct permissions on target sheet

### Sheet Access Tests
1. Verify bot can read from sheet
2. Verify bot can write to sheet
3. Verify proper error handling for access issues

## Sync Monitoring

Monitor these aspects during testing:
- **Sync Frequency:** How often changes propagate
- **Error Rates:** Failed sync attempts
- **Data Latency:** Time between database change and sheet update
- **Conflict Resolution:** How conflicting changes are handled

## Troubleshooting Common Issues

### Sync Failures
- Check Google Cloud credentials
- Verify sheet permissions
- Check network connectivity
- Review error logs

### Data Discrepancies
- Compare database and sheet data manually
- Check for timezone issues
- Verify data type conversions
- Review audit logs for missed updates

### Performance Issues
- Monitor API rate limits
- Check for large batch operations
- Verify sheet isn't overloaded
- Review sync queue length
