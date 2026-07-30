Attribute VB_Name = "RunHillstoneJobsFromAPI"
Option Explicit

Private Const API_BASE_URL As String = "http://10.115.2.61:12010"
Private Const POLL_INTERVAL_SECONDS As Long = 5
Private Const JOB_TIMEOUT_MINUTES As Long = 30


' Replaces the old local cmd/python call.
' Runs export first and starts insert only when export succeeds.
Public Sub Run_Python_Hillstone()
    Dim exportJobId As String
    Dim insertJobId As String

    On Error GoTo ErrorHandler

    exportJobId = StartApiJob("/jobs/export-hillstone")
    If Not WaitForApiJob(exportJobId, "Export Hillstone") Then
        Err.Raise vbObjectError + 2000, _
                  "Run_Python_Hillstone", _
                  "Export job failed. Job ID: " & exportJobId & vbCrLf & _
                  "Log: " & API_BASE_URL & "/jobs/" & exportJobId & "/log"
    End If

    insertJobId = StartApiJob("/jobs/insert-log")
    If Not WaitForApiJob(insertJobId, "Insert PostgreSQL") Then
        Err.Raise vbObjectError + 2001, _
                  "Run_Python_Hillstone", _
                  "Insert job failed. Job ID: " & insertJobId & vbCrLf & _
                  "Log: " & API_BASE_URL & "/jobs/" & insertJobId & "/log"
    End If

    Application.StatusBar = False
    MsgBox "Export and insert jobs completed successfully.", _
           vbInformation, _
           "Hillstone API"
    Exit Sub

ErrorHandler:
    Application.StatusBar = False
    MsgBox "Hillstone job failed: " & Err.Description, _
           vbExclamation, _
           "Hillstone API"
End Sub


Public Sub Run_Export_Hillstone_API()
    RunSingleApiJob "/jobs/export-hillstone", "Export Hillstone"
End Sub


Public Sub Run_Insert_Log_API()
    RunSingleApiJob "/jobs/insert-log", "Insert PostgreSQL"
End Sub


Private Sub RunSingleApiJob( _
    ByVal endpoint As String, _
    ByVal displayName As String)

    Dim jobId As String

    On Error GoTo ErrorHandler

    jobId = StartApiJob(endpoint)
    If Not WaitForApiJob(jobId, displayName) Then
        Err.Raise vbObjectError + 2002, _
                  "RunSingleApiJob", _
                  displayName & " failed. Job ID: " & jobId & vbCrLf & _
                  "Log: " & API_BASE_URL & "/jobs/" & jobId & "/log"
    End If

    Application.StatusBar = False
    MsgBox displayName & " completed successfully.", _
           vbInformation, _
           "Hillstone API"
    Exit Sub

ErrorHandler:
    Application.StatusBar = False
    MsgBox displayName & " failed: " & Err.Description, _
           vbExclamation, _
           "Hillstone API"
End Sub


Private Function StartApiJob(ByVal endpoint As String) As String
    Dim http As Object
    Dim responseText As String

    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    http.SetTimeouts 30000, 30000, 30000, 30000
    http.Open "POST", API_BASE_URL & endpoint, False
    http.SetRequestHeader "Accept", "application/json"
    http.Send

    responseText = http.ResponseText

    If http.Status <> 202 Then
        Err.Raise vbObjectError + 2010, _
                  "StartApiJob", _
                  "API returned HTTP " & http.Status & ": " & responseText
    End If

    StartApiJob = GetJsonString(responseText, "job_id")
    If Len(StartApiJob) = 0 Then
        Err.Raise vbObjectError + 2011, _
                  "StartApiJob", _
                  "The API response does not contain job_id."
    End If
End Function


Private Function WaitForApiJob( _
    ByVal jobId As String, _
    ByVal displayName As String) As Boolean

    Dim http As Object
    Dim responseText As String
    Dim jobState As String
    Dim deadline As Date

    deadline = DateAdd("n", JOB_TIMEOUT_MINUTES, Now)

    Do
        DoEvents

        Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
        http.SetTimeouts 30000, 30000, 30000, 30000
        http.Open "GET", API_BASE_URL & "/jobs/" & jobId, False
        http.SetRequestHeader "Accept", "application/json"
        http.Send

        responseText = http.ResponseText

        If http.Status <> 200 Then
            Err.Raise vbObjectError + 2020, _
                      "WaitForApiJob", _
                      "API returned HTTP " & http.Status & ": " & responseText
        End If

        jobState = LCase$(GetJsonString(responseText, "state"))
        Application.StatusBar = displayName & _
                                " | Job: " & jobId & _
                                " | State: " & jobState

        Select Case jobState
            Case "succeeded"
                WaitForApiJob = True
                Exit Function

            Case "failed"
                WaitForApiJob = False
                Exit Function

            Case "queued", "running"
                ' Continue polling.

            Case Else
                Err.Raise vbObjectError + 2021, _
                          "WaitForApiJob", _
                          "Unknown job state: " & jobState
        End Select

        If Now >= deadline Then
            Err.Raise vbObjectError + 2022, _
                      "WaitForApiJob", _
                      displayName & " timed out after " & _
                      JOB_TIMEOUT_MINUTES & " minutes."
        End If

        Application.Wait Now + TimeSerial(0, 0, POLL_INTERVAL_SECONDS)
    Loop
End Function


Private Function GetJsonString( _
    ByVal jsonText As String, _
    ByVal propertyName As String) As String

    Dim marker As String
    Dim valueStart As Long
    Dim valueEnd As Long

    marker = """" & propertyName & """:"
    valueStart = InStr(1, jsonText, marker, vbTextCompare)
    If valueStart = 0 Then Exit Function

    valueStart = valueStart + Len(marker)
    Do While valueStart <= Len(jsonText) And _
             Mid$(jsonText, valueStart, 1) = " "
        valueStart = valueStart + 1
    Loop

    If Mid$(jsonText, valueStart, 1) <> """" Then Exit Function
    valueStart = valueStart + 1

    valueEnd = InStr(valueStart, jsonText, """")
    If valueEnd = 0 Then Exit Function

    GetJsonString = Mid$(jsonText, valueStart, valueEnd - valueStart)
End Function
