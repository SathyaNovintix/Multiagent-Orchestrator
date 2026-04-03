# Sample MOM Templates

This folder contains sample template files that demonstrate how to structure your custom MOM formats.

## How to Create a Custom Template

### Excel Template (.xlsx)

Create an Excel file with the following structure:

```
Row 1: Meeting Title / Header
Row 2: (blank)
Row 3: Topics Discussed          (Section Header)
Row 4: Title | Summary | Timestamp (Column Headers - optional)
Row 5-10: (sample data or leave blank)
Row 11: (blank)
Row 12: Decisions Made           (Section Header)
Row 13: Decision | Owner | Condition (Column Headers - optional)
Row 14-18: (sample data or leave blank)
Row 19: (blank)
Row 20: Action Items             (Section Header)
Row 21: Task | Owner | Deadline | Priority (Column Headers - optional)
Row 22-30: (sample data or leave blank)
```

### Word Template (.docx)

Create a Word document with the following structure:

```
Heading 1: Minutes of Meeting

Heading 2: Topics Discussed
- Topic 1
- Topic 2

Heading 2: Decisions Made
- Decision 1 (Owner: Name)
- Decision 2 (Owner: Name)

Heading 2: Action Items
- Task 1 (Owner: Name, Due: Date)
- Task 2 (Owner: Name, Due: Date)
```

## Supported Section Keywords

The parser recognizes these keywords to identify sections:

- **Topics**: topic, discussion, agenda
- **Decisions**: decision, agreed, resolution
- **Actions**: action, task, follow-up, next step
- **Participants**: participant, attendee
- **Summary**: summary, note, remark

## Field Keywords

For each section, these field names are recognized:

- **General**: title, name, description, summary
- **Ownership**: owner, responsible, assigned
- **Timing**: deadline, due date, date
- **Status**: priority, status, condition

## Tips

1. Use bold or heading styles for section headers
2. Keep section names clear and descriptive
3. The AI will extract content based on your template structure
4. Custom labels from your template will appear in the generated PDF
5. If parsing fails, the system falls back to standard format
