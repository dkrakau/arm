Attribute VB_Name = "Modul1"
Sub TextAlsNotiz()
    Dim z As Range
    Const BEREICH As String = "H2:Q14"

    For Each z In ActiveSheet.Range(BEREICH)
        If Len(z.Value) > 0 Then
            If Not z.Comment Is Nothing Then z.Comment.Delete
            z.AddComment CStr(z.Value)
            With z.Comment.Shape
                .TextFrame.AutoSize = True
                If .Width > 400 Then
                    .Height = .Height * .Width / 400 * 1.1
                    .Width = 400
                End If
            End With
        End If
    Next z
End Sub
