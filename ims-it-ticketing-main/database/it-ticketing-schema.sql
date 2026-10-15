CREATE TABLE AdminUsers (
  ID INT IDENTITY(1,1) PRIMARY KEY,
  Username NVARCHAR(80) NOT NULL UNIQUE,
  PasswordHash NVARCHAR(255) NOT NULL,
  Name NVARCHAR(160) NOT NULL,
  Role NVARCHAR(40) NOT NULL DEFAULT 'Admin',
  CreatedDate DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE Tickets (
  TicketID INT IDENTITY(1,1) PRIMARY KEY,
  TicketNumber NVARCHAR(20) NOT NULL UNIQUE,
  EmployeeName NVARCHAR(160) NOT NULL,
  Department NVARCHAR(120) NOT NULL,
  Contact NVARCHAR(80) NOT NULL DEFAULT '',
  ComputerName NVARCHAR(120) NOT NULL,
  Category NVARCHAR(40) NOT NULL,
  Priority NVARCHAR(20) NOT NULL,
  Description NVARCHAR(MAX) NOT NULL,
  ScreenshotPath NVARCHAR(500) NULL,
  Status NVARCHAR(40) NOT NULL DEFAULT 'Pending',
  AssignedTechnician NVARCHAR(160) NULL,
  AdminNotes NVARCHAR(MAX) NULL,
  CreatedDate DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  UpdatedDate DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  ResolvedDate DATETIME2 NULL,
  CONSTRAINT CK_Tickets_Category CHECK (Category IN ('Hardware', 'Software', 'Network', 'Printer', 'Email', 'Account', 'Other')),
  CONSTRAINT CK_Tickets_Priority CHECK (Priority IN ('Low', 'Normal', 'High', 'Critical')),
  CONSTRAINT CK_Tickets_Status CHECK (Status IN ('Pending', 'In Progress', 'Waiting for User', 'Resolved', 'Closed', 'Cancelled'))
);

CREATE TABLE TicketLogs (
  LogID INT IDENTITY(1,1) PRIMARY KEY,
  TicketID INT NOT NULL,
  Action NVARCHAR(80) NOT NULL,
  OldStatus NVARCHAR(40) NULL,
  NewStatus NVARCHAR(40) NULL,
  Admin NVARCHAR(160) NULL,
  DateTime DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  Notes NVARCHAR(MAX) NULL,
  CONSTRAINT FK_TicketLogs_Tickets FOREIGN KEY (TicketID)
    REFERENCES Tickets (TicketID)
);

CREATE INDEX IX_Tickets_Search ON Tickets (
  TicketNumber,
  EmployeeName,
  ComputerName,
  Department,
  Category,
  Status,
  CreatedDate
);

CREATE INDEX IX_Tickets_Status_CreatedDate ON Tickets (Status, CreatedDate);
CREATE INDEX IX_TicketLogs_TicketID_DateTime ON TicketLogs (TicketID, DateTime DESC);
