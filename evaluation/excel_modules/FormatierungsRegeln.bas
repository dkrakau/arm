Attribute VB_Name = "Modul2"
Sub FormatierungsRegeln()
    Dim ws As Worksheet, start As Worksheet
    Const BEREICH As String = "A2:R14"

    Set start = ActiveSheet
    Application.ScreenUpdating = False

    For Each ws In ThisWorkbook.Worksheets
        If ws.Visible = xlSheetVisible Then
            ws.Activate
            ws.Range("A2").Select

            With ws.Range(BEREICH).FormatConditions
                .Delete

                With .Add(xlExpression, , "=$R2=""False""")
                    .Interior.Color = RGB(255, 130, 130)   'Rot
                    .SetFirstPriority
                End With

                With .Add(xlExpression, , "=$R2=""True""")
                    .Interior.Color = RGB(198, 224, 180)   'Grün
                    .SetFirstPriority
                End With

                With .Add(xlExpression, , "=A2=""""")
                    .Interior.Color = RGB(255, 255, 150)   'Gelb
                    .SetFirstPriority
                End With
            End With
        End If
    Next ws

    start.Activate
    Application.ScreenUpdating = True
End Sub
