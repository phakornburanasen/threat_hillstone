Attribute VB_Name = "ImportCSVFromAPI"
Option Explicit

Public Sub ImportCSVToLogHillstone()
    Const API_URL As String = _
        "http://10.115.2.61:12010/files/logs-hillstone.csv"

    Dim http As Object
    Dim fileStream As Object
    Dim csvWB As Workbook
    Dim csvWS As Worksheet
    Dim targetWB As Workbook
    Dim targetWS As Worksheet
    Dim tempFilePath As String
    Dim lastRow As Long
    Dim lastCol As Long
    Dim i As Long
    Dim errorDescription As String

    On Error GoTo ErrorHandler
    Application.ScreenUpdating = False

    tempFilePath = Environ$("TEMP") & _
        "\LogsHillstoneDaily_" & Format$(Now, "yyyymmdd_hhnnss") & ".csv"

    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    http.SetTimeouts 30000, 30000, 30000, 300000
    http.Open "GET", API_URL, False
    http.SetRequestHeader "Accept", "text/csv"
    http.Send

    If http.Status <> 200 Then
        Err.Raise vbObjectError + 1000, _
                  "ImportCSVToLogHillstone", _
                  "API returned HTTP " & http.Status & ": " & http.ResponseText
    End If

    Set fileStream = CreateObject("ADODB.Stream")
    fileStream.Type = 1
    fileStream.Open
    fileStream.Write http.ResponseBody
    fileStream.SaveToFile tempFilePath, 2
    fileStream.Close

    Workbooks.OpenText _
        Filename:=tempFilePath, _
        Origin:=65001, _
        DataType:=xlDelimited, _
        TextQualifier:=xlTextQualifierDoubleQuote, _
        Comma:=True, _
        Local:=True

    Set csvWB = ActiveWorkbook
    Set csvWS = csvWB.Worksheets(1)
    Set targetWB = ThisWorkbook
    Set targetWS = targetWB.Worksheets("Log")

    targetWS.Cells.Clear

    lastRow = csvWS.Cells(csvWS.Rows.Count, 1).End(xlUp).row
    lastCol = csvWS.Cells(1, csvWS.Columns.Count).End(xlToLeft).Column

    csvWS.Range( _
        csvWS.Cells(1, 1), _
        csvWS.Cells(lastRow, lastCol) _
    ).Copy
    targetWS.Range("A1").PasteSpecial Paste:=xlPasteValues
    Application.CutCopyMode = False

    Application.DisplayAlerts = False
    csvWB.Close SaveChanges:=False
    Application.DisplayAlerts = True
    Set csvWB = Nothing

    If Len(Dir$(tempFilePath)) > 0 Then Kill tempFilePath

    With targetWS
        For i = 2 To .Cells(.Rows.Count, "A").End(xlUp).row
            If IsDate(.Cells(i, "M").Value) Then
                .Cells(i, "M").Value = CDate(.Cells(i, "M").Value)
                .Cells(i, "M").NumberFormat = "dd/mm/yyyy hh:mm:ss"
            End If

            If IsDate(.Cells(i, "N").Value) Then
                .Cells(i, "N").Value = CDate(.Cells(i, "N").Value)
                .Cells(i, "N").NumberFormat = "dd/mm/yyyy hh:mm:ss"
            End If
        Next i
    End With

    Application.ScreenUpdating = True

    RunArrangeColumnsSafely targetWB, targetWS
    RunFormatDatesSafely targetWB, targetWS

    MsgBox "Imported LogsHillstoneDaily.csv from API.", _
           vbInformation, _
           "Success"
    Exit Sub

ErrorHandler:
    errorDescription = Err.Description
    On Error Resume Next
    Application.DisplayAlerts = False
    If Not csvWB Is Nothing Then csvWB.Close SaveChanges:=False
    Application.DisplayAlerts = True
    If Len(tempFilePath) > 0 Then
        If Len(Dir$(tempFilePath)) > 0 Then Kill tempFilePath
    End If
    Application.ScreenUpdating = True
    MsgBox "Import failed: " & errorDescription, vbExclamation, "Error"
End Sub

Private Sub PrepareLogSheetForFormatting( _
    ByVal targetWB As Workbook, _
    ByVal targetWS As Worksheet)

    If targetWB.Windows.Count = 0 Then
        Err.Raise vbObjectError + 1001, _
                  "PrepareLogSheetForFormatting", _
                  "The target workbook does not have an active window."
    End If

    targetWB.Activate
    targetWB.Windows(1).Activate
    targetWS.Activate

    If targetWB.Windows(1).View <> xlNormalView Then
        targetWB.Windows(1).View = xlNormalView
    End If

    Application.Goto targetWS.Range("A2"), True
    DoEvents
End Sub

Private Sub RunArrangeColumnsSafely( _
    ByVal targetWB As Workbook, _
    ByVal targetWS As Worksheet)

    Dim errorNumber As Long
    Dim errorDescription As String

    PrepareLogSheetForFormatting targetWB, targetWS

    On Error Resume Next
    No_1_ArrangeColumnsByPosition
    errorNumber = Err.Number
    errorDescription = Err.Description
    Err.Clear
    On Error GoTo 0

    If errorNumber <> 0 Then
        If InStr(1, errorDescription, "FreezePanes", vbTextCompare) = 0 Then
            Err.Raise errorNumber, _
                      "No_1_ArrangeColumnsByPosition", _
                      errorDescription
        End If
    End If
End Sub

Private Sub RunFormatDatesSafely( _
    ByVal targetWB As Workbook, _
    ByVal targetWS As Worksheet)

    Dim errorNumber As Long
    Dim errorDescription As String

    PrepareLogSheetForFormatting targetWB, targetWS

    On Error Resume Next
    FormatDateColumns_M_N
    errorNumber = Err.Number
    errorDescription = Err.Description
    Err.Clear
    On Error GoTo 0

    If errorNumber <> 0 Then
        If InStr(1, errorDescription, "FreezePanes", vbTextCompare) = 0 Then
            Err.Raise errorNumber, _
                      "FormatDateColumns_M_N", _
                      errorDescription
        End If
    End If
End Sub
