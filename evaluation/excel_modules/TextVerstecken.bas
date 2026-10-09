Attribute VB_Name = "Modul3"
Sub TextVerstecken()
    Dim ws As Worksheet
    Const BEREICH As String = "H2:Q14"

    For Each ws In ThisWorkbook.Worksheets
        ws.Range(BEREICH).NumberFormat = ";;;""" & ChrW(8230) & """"
    Next ws
End Sub
