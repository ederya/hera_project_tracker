import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from src.database import get_all_tasks_with_people, get_all_people
import io

def generate_excel(lang='EN'):
    """Generates an Excel file with multiple sheets, one for each person."""
    # Create a new workbook
    wb = openpyxl.Workbook()
    
    # Remove the default sheet created by openpyxl
    default_sheet = wb.active
    
    # Language setup
    if lang == 'TR':
        period_mapping = {
            1: "Bu Hafta",
            2: "Gelecek Hafta",
            3: "Bu Ay İçinde",
            4: "Beklemede"
        }
        headers = ["Aksiyon Adı", "Durum", "Hedef Dönem", "Kesin Tarih", "Sonuç"]
        open_text = "Açık"
        closed_text = "Kapalı"
        no_data_text = "Görev bulunamadı"
    else:
        period_mapping = {
            1: "This Week",
            2: "Next Week",
            3: "This Month",
            4: "On Hold"
        }
        headers = ["Action", "Status", "Target Period", "Exact Date", "Result"]
        open_text = "Open"
        closed_text = "Closed"
        no_data_text = "No tasks available"
    
    # Get all tasks joined with people
    data = get_all_tasks_with_people()
    all_people = get_all_people()
    
    # Group tasks by person
    people_tasks = {}
    for person in all_people:
        people_tasks[person['name']] = []
        
    for row in data:
        person_name = row['person_name']
        people_tasks[person_name].append(row)
        
    if not people_tasks:
        # If no data, just rename the default sheet and add headers
        default_sheet.title = "No Data"
        default_sheet.append([no_data_text])
    else:
        # We will remove the default sheet after creating our own
        is_first_sheet = True
        
        for person_name, tasks in people_tasks.items():
            # Create a sheet for the person
            sheet = wb.create_sheet(title=person_name)
            
            # If it's the first person, we can remove the default sheet
            if is_first_sheet:
                wb.remove(default_sheet)
                is_first_sheet = False
            
            # Define Borders
            thin_border = Border(
                left=Side(style='thin', color='000000'),
                right=Side(style='thin', color='000000'),
                top=Side(style='thin', color='000000'),
                bottom=Side(style='thin', color='000000')
            )

            # Add big title for person's name
            sheet.append([person_name.upper()])
            sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
            title_cell = sheet.cell(row=1, column=1)
            title_cell.font = Font(bold=True, size=16, color="000000")
            title_cell.fill = PatternFill("solid", fgColor="DDDDDD")
            title_cell.alignment = Alignment(horizontal="center", vertical="center")
            
            for col in range(1, 6):
                sheet.cell(row=1, column=col).border = thin_border
            
            # Define Headers
            sheet.append(headers)
            
            # Style the header row
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill("solid", fgColor="4682B4") # Steel Blue
            
            for cell in sheet[2]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
                cell.border = thin_border
            
            # Append tasks
            if not tasks:
                sheet.append([no_data_text])
                sheet.merge_cells(start_row=3, start_column=1, end_row=3, end_column=5)
            else:
                for task in tasks:
                    target_period = period_mapping.get(task['target_period_id'], "Unknown")
                    exact_date = task['exact_date'] if task['is_exact_date_active'] else "-"
                    result_translated = open_text if task['result'] == 'Open' else closed_text
                    
                    sheet.append([
                        task['action_name'],
                        task['status'],
                        target_period,
                        exact_date,
                        result_translated
                    ])
                
            # Adjust column widths to standard sizes (wider to fit screen)
            sheet.column_dimensions['A'].width = 50  # Action
            sheet.column_dimensions['B'].width = 70  # Status
            sheet.column_dimensions['C'].width = 20  # Target Period
            sheet.column_dimensions['D'].width = 20  # Exact Date
            sheet.column_dimensions['E'].width = 15  # Result
            
            # Apply wrap text and border to all data cells
            wrap_alignment = Alignment(wrap_text=True, vertical="top")
            for row in sheet.iter_rows(min_row=3):
                for cell in row:
                    cell.alignment = wrap_alignment
                    cell.border = thin_border

    # Save to a memory stream
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
